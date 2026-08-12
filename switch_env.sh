#!/bin/bash
# 一键切换 开发(dev/SQLite) / 生产(prod/PostgreSQL) 环境
# 用法:
#   ./switch_env.sh            来回切换（当前生产→开发，当前开发→生产）
#   ./switch_env.sh dev        切换到开发环境 (SQLite)
#   ./switch_env.sh prod       切换到生产环境 (PostgreSQL)
#   ./switch_env.sh status     查看状态

ROOT="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE=/tmp/testplatform_env
LOG=/tmp/testplatform_backend.log
PORT=8000

stop_backend() {
  local pids
  pids=$(lsof -ti:"$PORT" 2>/dev/null)
  if [ -n "$pids" ]; then
    echo "停止当前后端 (PID: $pids)..."
    kill $pids 2>/dev/null
    sleep 2
  fi
}

start_backend() {
  local env="$1"
  echo "启动 ${env} 环境后端..."
  cd "$ROOT/backend"
  if [ "$env" = "prod" ]; then
    APP_ENV=prod nohup python3 run.py > "$LOG" 2>&1 &
  else
    APP_ENV=dev nohup python3 run.py > "$LOG" 2>&1 &
  fi
  echo "$env" > "$ENV_FILE"
  for i in $(seq 1 25); do
    sleep 1
    if curl -sf http://localhost:$PORT/api/v1/health >/dev/null 2>&1; then
      echo "✅ 后端已就绪: http://localhost:$PORT/api/v1/health"
      return 0
    fi
  done
  echo "❌ 后端启动超时，查看日志: $LOG"
  return 1
}

show_status() {
  echo "=============================================="
  echo "  测试平台 环境状态"
  echo "=============================================="
  if [ -f "$ENV_FILE" ]; then
    local env
    env=$(cat "$ENV_FILE")
    if [ "$env" = "prod" ]; then
      echo "  当前环境 : 生产 (PostgreSQL)"
    else
      echo "  当前环境 : 开发 (SQLite)"
    fi
  else
    echo "  当前环境 : 未知（尚未用本脚本启动）"
  fi
  echo "  ─────────────────────────────────────────"
  echo "  后端 :8000  : $([ -n "$(lsof -ti:$PORT 2>/dev/null)" ] && echo '运行中' || echo '未运行')"
  echo "  PostgreSQL :5432 : $([ -n "$(lsof -ti:5432 2>/dev/null)" ] && echo '运行中' || echo '未运行')"
  echo "  Redis :6379 : $([ -n "$(lsof -ti:6379 2>/dev/null)" ] && echo '运行中' || echo '未运行')"
  echo "  前端 :5173  : $([ -n "$(lsof -ti:5173 2>/dev/null)" ] && echo '运行中' || echo '未运行')"
  echo "  ─────────────────────────────────────────"
  echo "  提示: 开发环境数据库=SQLite, 生产环境数据库=PostgreSQL"
  echo "  切换: ./switch_env.sh dev  /  ./switch_env.sh prod"
}

case "$1" in
  dev|prod)
    stop_backend
    start_backend "$1"
    echo ""
    show_status
    ;;
  ""|-t|--toggle)
    # 直接运行 = 来回切换：生产↔开发轮换；从未启动过则默认切到生产
    if [ -f "$ENV_FILE" ] && [ "$(cat "$ENV_FILE")" = "prod" ]; then
      target=dev
    else
      target=prod
    fi
    stop_backend
    start_backend "$target"
    echo ""
    show_status
    ;;
  status|-s|--status)
    show_status
    ;;
  *)
    echo "用法: $0 [dev|prod|status]"
    echo "  直接运行 $0 : 生产↔开发 来回切换"
    exit 1
    ;;
esac
