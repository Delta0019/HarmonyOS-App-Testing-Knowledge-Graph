#!/usr/bin/env bash
# =============================================================================
# run_overnight.sh — 通宵批量测试脚本 (KG+UTG 模式)
#
# 用法:
#   bash run_overnight.sh                    # 默认: gui-owl-7b, 无限轮
#   bash run_overnight.sh --max_rounds 5     # 最多跑5轮
#   bash run_overnight.sh --model gui-owl-32b
#
# 停止: Ctrl+C (等当前任务跑完后优雅退出)
# 强制停止: 连按两次 Ctrl+C
# =============================================================================

set -o pipefail

# ======================== 可配置参数 ========================
MODEL="gui-owl-7b"
API_KEY="EMPTY"
BASE_URL="http://127.0.0.1:8000/v1"
MAX_ROUNDS=0  # 0 = 无限
N_TASK_COMBINATIONS=1

# 路径配置
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ANDROID_SDK_ROOT="/opt/homebrew/share/android-commandlinetools"
KG_PROJECT_PATH="/Users/bytedance/Desktop/graduate/HarmonyOS-App-Testing-Knowledge-Graph"
EMBEDDING_MODEL="paraphrase-multilingual-MiniLM-L12-v2"
VENV="$SCRIPT_DIR/.venv/bin"
SSH_KEY="$HOME/.ssh/id_ed25519_liangyu"
GPU_SERVER="zyc@172.18.36.55"

# 结果目录
SESSION_DATE=$(date +"%Y%m%d")
RESULTS_BASE="$SCRIPT_DIR/results/overnight_${SESSION_DATE}"
UTG_SHARED="$RESULTS_BASE/utg.json"

# ======================== 参数解析 ========================
while [[ $# -gt 0 ]]; do
    case $1 in
        --model) MODEL="$2"; shift 2 ;;
        --max_rounds) MAX_ROUNDS="$2"; shift 2 ;;
        --results_dir) RESULTS_BASE="$2"; shift 2 ;;
        --base_url) BASE_URL="$2"; shift 2 ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# ======================== 环境变量 ========================
export ANDROID_SDK_ROOT
export PATH="$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/emulator:/opt/homebrew/opt/openjdk/bin:$PATH"

# ======================== 信号处理 ========================
STOP_REQUESTED=0
FORCE_STOP=0

trap_handler() {
    if [[ $STOP_REQUESTED -eq 1 ]]; then
        echo ""
        echo "$(tput bold)$(tput setaf 1)[强制停止] 立即终止$(tput sgr0)"
        FORCE_STOP=1
        # 杀掉子进程
        kill 0 2>/dev/null
        exit 1
    fi
    STOP_REQUESTED=1
    echo ""
    echo "$(tput bold)$(tput setaf 3)[收到停止信号] 等待当前轮次完成后退出...$(tput sgr0)"
    echo "  (再按一次 Ctrl+C 强制终止)"
}

trap trap_handler SIGINT SIGTERM

# ======================== 工具函数 ========================

log() {
    echo "[$(date '+%H:%M:%S')] $*"
}

log_section() {
    echo ""
    echo "$(tput bold)$(tput setaf 6)═══════════════════════════════════════════════════════════$(tput sgr0)"
    echo "$(tput bold)$(tput setaf 6)  $*$(tput sgr0)"
    echo "$(tput bold)$(tput setaf 6)═══════════════════════════════════════════════════════════$(tput sgr0)"
}

check_emulator() {
    adb devices 2>/dev/null | grep -q "emulator" && return 0
    log "模拟器未运行，正在启动..."
    emulator -avd AndroidWorldAvd -no-window -no-audio -grpc 8554 -no-snapshot -no-metrics &>/tmp/emulator_overnight.log &
    # 等待启动
    for i in $(seq 1 60); do
        sleep 3
        if adb devices 2>/dev/null | grep -q "device$"; then
            BOOT=$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')
            if [[ "$BOOT" == "1" ]]; then
                log "模拟器启动成功 (${i}x3s)"
                return 0
            fi
        fi
    done
    log "错误: 模拟器启动超时"
    return 1
}

check_model_service() {
    curl -s --connect-timeout 3 "$BASE_URL/models" 2>/dev/null | grep -q "$MODEL" && return 0

    log "模型服务不可用，尝试重建端口转发..."
    # 杀掉已有的端口转发
    pkill -f "ssh.*-L 8000:127.0.0.1:8000.*$GPU_SERVER" 2>/dev/null
    sleep 1
    ssh -i "$SSH_KEY" -f -N -L 8000:127.0.0.1:8000 "$GPU_SERVER" 2>/dev/null

    # 等待服务可用
    for i in $(seq 1 12); do
        sleep 5
        if curl -s --connect-timeout 3 "$BASE_URL/models" 2>/dev/null | grep -q "$MODEL"; then
            log "模型服务已恢复"
            return 0
        fi
        log "  等待模型服务... ($i/12)"
    done

    log "错误: 模型服务无法恢复，请检查 GPU 服务器"
    return 1
}

extract_summary() {
    # 从 log 文件中提取摘要表格
    local logfile="$1"
    if [[ -f "$logfile" ]]; then
        grep -A2 "========= Average =========" "$logfile" 2>/dev/null || echo "  (无摘要数据)"
    fi
}

# ======================== 主逻辑 ========================

log_section "通宵批量测试启动"
log "模式: KG+UTG | 模型: $MODEL"
log "结果目录: $RESULTS_BASE"
log "最大轮数: $([ $MAX_ROUNDS -eq 0 ] && echo '无限' || echo $MAX_ROUNDS)"
log "停止方式: Ctrl+C (优雅) / Ctrl+C x2 (强制)"

mkdir -p "$RESULTS_BASE"

# 写入 session 元信息
cat > "$RESULTS_BASE/session_info.json" <<EOF
{
    "start_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "model": "$MODEL",
    "mode": "kg_utg",
    "kg_project": "$KG_PROJECT_PATH",
    "embedding_model": "$EMBEDDING_MODEL",
    "n_task_combinations": $N_TASK_COMBINATIONS
}
EOF

ROUND=0
TOTAL_TASKS=0
TOTAL_SUCCESS=0
SESSION_START=$(date +%s)

while true; do
    ROUND=$((ROUND + 1))

    # 检查是否达到最大轮数
    if [[ $MAX_ROUNDS -gt 0 && $ROUND -gt $MAX_ROUNDS ]]; then
        log "已达到最大轮数 ($MAX_ROUNDS)，退出"
        break
    fi

    # 检查停止标记
    if [[ $STOP_REQUESTED -eq 1 ]]; then
        break
    fi

    log_section "第 $ROUND 轮"

    # ---- 健康检查 ----
    log "健康检查..."
    if ! check_emulator; then
        log "跳过本轮 (模拟器故障)"
        sleep 10
        continue
    fi
    if ! check_model_service; then
        log "跳过本轮 (模型服务故障)"
        sleep 10
        continue
    fi
    log "健康检查通过 ✓"

    # ---- 创建本轮目录 ----
    ROUND_DIR="$RESULTS_BASE/round_${ROUND}"
    ROUND_LOG="$RESULTS_BASE/round_${ROUND}.log"
    mkdir -p "$ROUND_DIR"

    ROUND_START=$(date +%s)

    # ---- 执行 ----
    log "开始执行 (日志: round_${ROUND}.log)"

    "$VENV/python" "$SCRIPT_DIR/run_ma3.py" \
        --suite_family=android_world \
        --agent_name=mobile_agent_v3 \
        --model="$MODEL" \
        --api_key="$API_KEY" \
        --base_url="$BASE_URL" \
        --grpc_port=8554 \
        --console_port=5554 \
        --n_task_combinations="$N_TASK_COMBINATIONS" \
        --output_path="$ROUND_DIR" \
        --use_utg \
        --utg_path="$UTG_SHARED" \
        --use_kg \
        --kg_project_path="$KG_PROJECT_PATH" \
        --embedding_model="$EMBEDDING_MODEL" \
        2>&1 | tee "$ROUND_LOG"

    EXIT_CODE=${PIPESTATUS[0]}
    ROUND_END=$(date +%s)
    ROUND_ELAPSED=$(( ROUND_END - ROUND_START ))
    ROUND_MIN=$(( ROUND_ELAPSED / 60 ))

    # ---- 本轮摘要 ----
    echo ""
    if [[ $EXIT_CODE -eq 0 ]]; then
        log "$(tput setaf 2)第 $ROUND 轮完成$(tput sgr0) (耗时 ${ROUND_MIN}分钟)"
    else
        log "$(tput setaf 1)第 $ROUND 轮异常退出 (exit=$EXIT_CODE)$(tput sgr0) (耗时 ${ROUND_MIN}分钟)"
    fi
    extract_summary "$ROUND_LOG"

    # 统计本轮结果
    ROUND_TASKS=$(grep -c "\.pkl\.gz" "$ROUND_DIR"/*.pkl.gz 2>/dev/null || find "$ROUND_DIR" -name "*.pkl.gz" 2>/dev/null | wc -l | tr -d ' ')
    ROUND_SUCCESS=$(grep -c "Task Succeeded" "$ROUND_LOG" 2>/dev/null || echo 0)
    TOTAL_TASKS=$((TOTAL_TASKS + ROUND_TASKS))
    TOTAL_SUCCESS=$((TOTAL_SUCCESS + ROUND_SUCCESS))

    # 写入本轮结果
    cat > "$ROUND_DIR/round_summary.json" <<EOFR
{
    "round": $ROUND,
    "exit_code": $EXIT_CODE,
    "elapsed_seconds": $ROUND_ELAPSED,
    "tasks_run": $ROUND_TASKS,
    "tasks_succeeded": $ROUND_SUCCESS,
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOFR

    # 检查停止标记
    if [[ $STOP_REQUESTED -eq 1 ]]; then
        break
    fi

    # 轮间短暂休息，让模拟器恢复
    log "休息 15 秒后开始下一轮..."
    sleep 15
done

# ======================== 最终摘要 ========================

SESSION_END=$(date +%s)
SESSION_ELAPSED=$(( SESSION_END - SESSION_START ))
SESSION_HOURS=$(( SESSION_ELAPSED / 3600 ))
SESSION_MINS=$(( (SESSION_ELAPSED % 3600) / 60 ))

log_section "测试结束 - 总结"
echo "  总轮数:       $ROUND"
echo "  总任务数:     $TOTAL_TASKS"
echo "  总成功数:     $TOTAL_SUCCESS"
if [[ $TOTAL_TASKS -gt 0 ]]; then
    RATE=$(echo "scale=1; $TOTAL_SUCCESS * 100 / $TOTAL_TASKS" | bc 2>/dev/null || echo "N/A")
    echo "  总成功率:     ${RATE}%"
fi
echo "  总耗时:       ${SESSION_HOURS}小时${SESSION_MINS}分钟"
echo "  结果目录:     $RESULTS_BASE"
echo "  UTG 数据:     $UTG_SHARED"

# 写入总结
cat > "$RESULTS_BASE/final_summary.json" <<EOF
{
    "end_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "total_rounds": $ROUND,
    "total_tasks": $TOTAL_TASKS,
    "total_succeeded": $TOTAL_SUCCESS,
    "elapsed_seconds": $SESSION_ELAPSED,
    "stopped_by": "$([ $STOP_REQUESTED -eq 1 ] && echo 'user' || echo 'max_rounds')"
}
EOF

log "结果已保存到: $RESULTS_BASE"
