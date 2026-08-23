#!/bin/bash
# PostgreSQL 自动备份脚本
# 用法: ./backup_pg.sh [保留天数，默认30]
#
# 配合 crontab 使用：
#   每天凌晨 2 点备份：0 2 * * * /path/to/backup_pg.sh
#   每 6 小时备份一次：0 */6 * * * /path/to/backup_pg.sh

set -euo pipefail

# ── 配置 ──
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-testplatform}"
DB_USER="${DB_USER:-testplatform}"
DB_PASSWORD="${DB_PASSWORD:-testplatform123}"

BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${1:-30}"

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/testplatform_${DATE}.sql.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"

# ── 创建备份目录 ──
mkdir -p "${BACKUP_DIR}"

# ── 执行备份 ──
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始备份数据库 ${DB_NAME}..." >> "${LOG_FILE}"

PGPASSWORD="${DB_PASSWORD}" pg_dump \
  -h "${DB_HOST}" \
  -p "${DB_PORT}" \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  --no-owner \
  --no-privileges \
  2>> "${LOG_FILE}" | gzip > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
  SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份成功: ${BACKUP_FILE} (${SIZE})" >> "${LOG_FILE}"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份失败!" >> "${LOG_FILE}"
  exit 1
fi

# ── 清理过期备份 ──
DELETED=$(find "${BACKUP_DIR}" -name "testplatform_*.sql.gz" -mtime +${KEEP_DAYS} -delete -print | wc -l)
if [ "${DELETED}" -gt 0 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 已清理 ${DELETED} 个过期备份（>${KEEP_DAYS}天）" >> "${LOG_FILE}"
fi

# ── 显示当前备份情况 ──
TOTAL=$(ls -1 "${BACKUP_DIR}"/testplatform_*.sql.gz 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 当前共 ${TOTAL} 个备份，占用 ${TOTAL_SIZE}" >> "${LOG_FILE}"
