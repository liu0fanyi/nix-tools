#!/usr/bin/env bash
# DeepSeek 峰谷状态检查/标记
# 用法:
#   ./scripts/check-deepseek-load.sh          # 检测并写入状态（有 key 测延迟；无 key 提示手动标记）
#   ./scripts/check-deepseek-load.sh peak     # 手动标记高峰
#   ./scripts/check-deepseek-load.sh off      # 手动标记低谷
#   ./scripts/check-deepseek-load.sh status   # 查看当前状态
#
# 状态文件: ~/.dsh/peak-status（内容: peak|off-peak + 时间戳）
# 约定: AI 助手每轮开始检查此文件，peak 时警告用户并暂停工作。
set -euo pipefail

STATUS_FILE="${DSH_PEAK_FILE:-$HOME/.dsh/peak-status}"
LATENCY_THRESHOLD_S="${LATENCY_THRESHOLD_S:-5}"

write_status() {
  mkdir -p "$(dirname "$STATUS_FILE")"
  printf '%s %s\n' "$1" "$(date '+%Y-%m-%d %H:%M:%S %z')" > "$STATUS_FILE"
  echo "✅ 已标记: $(cat "$STATUS_FILE")"
}

case "${1:-detect}" in
  peak)
    write_status peak
    exit 0
    ;;
  off)
    write_status off-peak
    exit 0
    ;;
  status)
    if [ -f "$STATUS_FILE" ]; then
      echo "当前状态: $(cat "$STATUS_FILE")"
    else
      echo "无状态记录（默认 off-peak）"
    fi
    exit 0
    ;;
esac

# 自动检测模式：需要 API key
if [ -z "${DEEPSEEK_API_KEY:-}" ]; then
  echo "⚠️  未设置 DEEPSEEK_API_KEY，无法自动测延迟。"
  echo "   手动标记: $0 peak|off   或查看: $0 status"
  exit 2
fi

echo "检测 DeepSeek API 延迟（阈值 ${LATENCY_THRESHOLD_S}s）..."
START=$(date +%s.%N)
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -m 30 \
  https://api.deepseek.com/models \
  -H "Authorization: Bearer ${DEEPSEEK_API_KEY}" || true)
END=$(date +%s.%N)
LATENCY=$(echo "$END $START" | awk '{printf "%.2f", $1-$2}')
echo "HTTP=$HTTP 延迟=${LATENCY}s"

if [ "$HTTP" = "200" ] && awk "BEGIN{exit !($LATENCY < $LATENCY_THRESHOLD_S)}"; then
  write_status off-peak
elif [ "$HTTP" = "200" ]; then
  write_status peak
  echo "⚠️  高峰！延迟 ${LATENCY}s 超过阈值 ${LATENCY_THRESHOLD_S}s"
else
  echo "❌ API 异常（HTTP=$HTTP），保持原状态"
  exit 1
fi
