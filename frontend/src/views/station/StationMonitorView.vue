<template>
  <div class="station-monitor">
    <!-- Header -->
    <div class="monitor-header">
      <div class="header-left">
        <div class="station-title">
          <span class="status-dot" :class="wsConnected ? 'online' : 'offline'" />
          <h1 v-if="station" class="station-name">{{ station.name }}</h1>
          <span v-if="station" class="station-badge">{{ station.process_type }}{{ station.workstation ? ' / ' + station.workstation : '' }}</span>
        </div>
        <div class="station-meta">
          <span v-if="station">IP: {{ equipIP }}</span>
          <span v-if="station">ID: {{ stationId }}</span>
          <span v-if="currentVersionLabel" class="version-badge">{{ currentVersionLabel }}</span>
        </div>
      </div>
      <div class="header-right">
        <el-tag v-if="wsConnected" type="success" size="small">连线</el-tag>
        <el-tag v-else type="danger" size="small">断线</el-tag>
        <el-button size="small" class="param-btn" @click="openParamsPanel">
          <el-icon><Setting /></el-icon> 参数设置
        </el-button>
        <el-button size="small" class="param-btn" @click="showLogPanel = !showLogPanel">
          <el-icon><Memo /></el-icon> 日志
        </el-button>
      </div>
    </div>

    <!-- BOM / Process Info Bar -->
    <div v-if="selectedVersionBom || selectedSubScenario" class="version-info-bar">
      <div class="info-item">
        <span class="info-label">BOM 编码</span>
        <span class="info-value">{{ selectedBoms || selectedVersionBom }}</span>
      </div>
      <div v-if="selectedSubScenario" class="info-item">
        <span class="info-label">工序</span>
        <span class="info-value">{{ selectedSubScenario.process_type }}{{ selectedSubScenario.workstation ? '/' + selectedSubScenario.workstation : '' }}</span>
      </div>
    </div>

      <!-- Main Content -->
      <div class="main-content">
      <!-- Loading -->
      <div v-if="loading" class="loading-state">
        <el-icon class="is-loading" :size="40"><Loading /></el-icon>
        <p>加载装备信息...</p>
      </div>

      <!-- Error -->
      <div v-else-if="detailError" class="error-state">{{ detailError }}</div>

      <!-- Main Equipment View -->
      <div v-else class="equipment-view" :class="{ 'single-cab': cabinets.length === 1 }"
        @contextmenu.prevent="showStationMenu($event, stationId)"
        title="右键菜单"
      >
        <!-- Cabinet Row -->
        <div v-if="cabinets.length === 0" class="empty-cabinets">
          <el-icon :size="32"><FolderOpened /></el-icon>
          <p>该装备暂无机柜</p>
        </div>
        <div v-else class="cabinet-row">
          <div
            v-for="cab in cabinets"
            :key="cab.id"
            class="cabinet-unit"
            @contextmenu.stop.prevent="showCabinetMenu($event, cab)"
          >
            <div class="cabinet-unit-header">
              <span class="cabinet-unit-name">{{ cab.name }}</span>
              <span class="cabinet-param-link" @click.stop="showCabinetParams(cab.id)">
                <el-icon><Setting /></el-icon>
              </span>
            </div>

            <!-- Chassis inside cabinet -->
            <div class="chassis-list">
              <div
                v-for="ch in cab.chassis_list"
                :key="ch.id"
                class="chassis-unit"
                @contextmenu.stop.prevent="showChassisMenu($event, ch)"
              >
                <div class="chassis-unit-header">
                  <span class="chassis-unit-name">{{ ch.name }}</span>
                  <span class="chassis-slot-count">{{ ch.slot_count }} 槽</span>
                  <span class="chassis-param-link" @click.stop="showChassisParams(ch.id)">
                    <el-icon><Setting /></el-icon>
                  </span>
                </div>

                <!-- Slots grid -->
                <div class="slot-grid" :style="{ gridTemplateColumns: 'repeat(' + ch.slots.length + ', 1fr)' }">
                  <div
                    v-for="slot in ch.slots"
                    :key="slot.id"
                    class="slot-cell"
                    :class="'slot-' + slot.status"
                    @click="selectSlot(slot)"
                    @dblclick="openScanDialog(slot)"
                    @contextmenu.stop.prevent="showSlotMenu($event, slot, ch)"
                  >
                    <div class="slot-led" :class="'led-' + slot.status" />
                    <div class="slot-name">{{ slot.name.replace('槽位 ', 'S') }}</div>
                    <div v-if="slot.serial_number" class="slot-sn" :title="slot.serial_number">{{ slot.serial_number }}</div>
                    <div class="slot-status">{{ slotStatusLabel(slot.status) }}</div>
                    <div class="slot-progress" :class="{ active: slot.status === 'testing' }">
                      <div class="slot-progress-bar" :style="{ width: slot.status === 'pass' ? '100%' : slot.status === 'fail' ? '100%' : slot.status === 'testing' ? '60%' : '0%' }" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Params Panel (right side) -->
      <div v-if="paramsVisible" class="params-panel">
        <div class="params-panel-header">
          <span class="params-panel-title">{{ paramsTitle }}</span>
          <el-button size="small" :icon="Close" text @click="paramsVisible = false" />
        </div>
        <div class="params-panel-body">
          <el-tabs v-model="paramsTab" class="params-tabs">
            <!-- 装备参数 -->
            <el-tab-pane label="装备参数" name="equipment">
              <div v-if="equipForm" class="param-section-card">
                <div class="param-section-title">公共属性</div>
                <el-form :model="equipForm" label-width="90px">
                  <el-form-item label="装备 IP">
                    <el-input v-model="equipForm.equipment_ip" placeholder="192.168.1.100" size="small" />
                  </el-form-item>
                  <el-form-item label="服务地址">
                    <el-input v-model="equipForm.equipment_service_address" placeholder="http://192.168.1.100:8080/api" size="small" />
                    <div class="el-form-item__hint" style="margin-top:4px;color:#909399;font-size:0.7rem;">
                      基础 URL，测试项只需填相对路径（如 /test/tx-power），运行时自动拼接
                    </div>
                  </el-form-item>
                </el-form>
              </div>
              <div v-if="equipForm" class="param-section-card">
                <div class="param-section-title">通用属性</div>
                <el-form :model="equipForm" label-position="top">
                  <el-row :gutter="8">
                    <el-col :span="8">
                      <el-form-item label="正常测试" class="mb-1">
                        <el-switch v-model="equipForm.test_mode_normal" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="验证测试" class="mb-1">
                        <el-switch v-model="equipForm.test_mode_verify" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="校准测试" class="mb-1">
                        <el-switch v-model="equipForm.test_mode_calibration" />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  <el-row :gutter="8">
                    <el-col :span="8">
                      <el-form-item label="条码校验" class="mb-1">
                        <el-switch v-model="equipForm.barcode_verify_enabled" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="自动上板" class="mb-1">
                        <el-switch v-model="equipForm.auto_load_enabled" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="调试模式" class="mb-1">
                        <el-switch v-model="equipForm.debug_mode_enabled" />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  <el-form-item label="工序管控" class="mb-1">
                    <el-switch v-model="equipForm.process_control_enabled" />
                  </el-form-item>
                </el-form>
              </div>
              <div v-if="equipForm" class="text-right">
                <el-button type="primary" size="small" :loading="paramsSaving" @click="saveEquipParams">保存装备参数</el-button>
              </div>
              <div v-if="!equipForm" class="text-center text-gray-400 py-4">加载中...</div>
            </el-tab-pane>

            <!-- 硬件参数 -->
            <el-tab-pane label="硬件参数" name="hardware">
              <div class="mb-2 flex gap-2">
                <el-button type="primary" size="small" @click="openHwDialog()">新建参数</el-button>
                <el-button size="small" @click="showBatchReplace = true">批量替换</el-button>
                <el-button size="small" @click="refreshHardware" :loading="paramsSaving">刷新</el-button>
              </div>
              <el-table :data="hwList" stripe size="small" max-height="320" style="width:100%">
                <el-table-column prop="param_name" label="参数名" />
                <el-table-column prop="param_value" label="参数值" />
                <el-table-column prop="group_name" label="分组" width="80" />
                <el-table-column prop="sort_order" label="排序" width="50" />
                <el-table-column label="操作" width="120" fixed="right">
                  <template #default="{ row }">
                    <el-button size="small" link @click="openHwDialog(row)">编辑</el-button>
                    <el-button size="small" link type="danger" @click="deleteHw(row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>

            <!-- 软件参数 -->
            <el-tab-pane label="软件参数" name="software">
              <div class="version-cascade mb-3 p-3 param-section-card">
                <div class="param-section-title">版本选择</div>
                <el-form label-width="75px" label-position="top">
                  <el-form-item label="版本名称" class="mb-2">
                    <el-select v-model="selectedVersionId" filterable placeholder="选择已发行版本" @change="onVersionChange" style="width:100%">
                      <el-option v-for="v in deployedVersions" :key="v.version_id" :label="`${v.project_name} v${v.version}`" :value="v.version_id" />
                    </el-select>
                  </el-form-item>
                  <el-row :gutter="8">
                    <el-col :span="12">
                      <el-form-item label="BOM 编码" class="mb-2">
                        <el-select v-model="selectedBoms" filterable placeholder="选择 BOM" style="width:100%" size="small">
                          <el-option v-for="b in bomOptions" :key="b" :label="b" :value="b" />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="10">
                      <el-form-item label="子场景" class="mb-2">
                        <el-select v-model="selectedSubScenarioId" filterable placeholder="选择子场景" @change="onSubScenarioChange" style="width:100%" size="small">
                          <el-option v-for="s in subScenarios" :key="s.id" :label="s.name" :value="s.id">
                            <div class="flex items-center gap-2">
                              <span>{{ s.name }}</span>
                              <span v-if="s.process_type" class="text-gray-400 text-xs">{{ s.process_type }}{{ s.workstation ? '/' + s.workstation : '' }}</span>
                            </div>
                          </el-option>
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="2" class="flex items-end pb-2">
                      <el-button :disabled="!selectedVersionId" size="small" circle @click="loadSubScenarios">
                        <el-icon><Refresh /></el-icon>
                      </el-button>
                    </el-col>
                  </el-row>
                  <div v-if="selectedSubScenario" class="flex gap-2 mt-1 flex-wrap">
                    <el-tag size="small" type="info">序列: {{ selectedSubScenario.sequence_id || '未配置' }}</el-tag>
                    <el-tag size="small" type="success">硬件: {{ selectedSubScenario.hardware_params ? Object.keys(selectedSubScenario.hardware_params).length + ' 项' : '0 项' }}</el-tag>
                    <el-tag size="small" type="warning">文件: {{ (selectedSubScenario.binary_files || []).length }} 个</el-tag>
                  </div>
                </el-form>
              </div>
              <div v-if="softForm">
                <div class="param-section-title">测试项</div>
                <div v-if="sequenceSteps.length > 0" class="test-items-list" style="max-height:280px;">
                  <div
                    v-for="s in sequenceSteps"
                    :key="s.test_item_id || s.id"
                    class="test-item-row"
                  >
                    <div class="test-item-name" :class="{ critical: s.is_critical || s.template_is_critical }">
                      {{ s.test_item_name || s.template_name || '未知测试项' }}
                    </div>
                    <div class="test-item-tags">
                      <el-tag v-if="s.test_type || s.template_category" class="test-item-tag type">
                        {{ s.test_type || s.template_category }}
                      </el-tag>
                      <el-tag v-if="s.is_critical || s.template_is_critical" class="test-item-tag critical">关键</el-tag>
                      <el-tag v-if="s.block_type && s.block_type !== 'normal'" class="test-item-tag block">
                        {{ s.block_type }}
                      </el-tag>
                    </div>
                    <div v-if="s.service_address || s.template_service_address" class="test-item-service" :title="s.service_address || s.template_service_address">
                      {{ s.service_address || s.template_service_address }}
                    </div>
                    <el-checkbox v-model="stepCheckMap[s.test_item_id || s.id]" size="small" class="test-item-checkbox" />
                  </div>
                </div>
                <div v-else-if="selectedSubScenario" class="text-gray-400 text-sm mb-2" style="padding: 8px 4px;">该子场景未配置测试序列</div>
                <div class="text-right mt-2">
                  <el-button type="primary" size="small" :loading="paramsSaving" @click="saveSoftParams">保存软件参数</el-button>
                </div>
              </div>
              <div v-else class="text-center text-gray-400 py-4">加载中...</div>
            </el-tab-pane>

            <!-- 场景参数 -->
            <el-tab-pane label="场景参数" name="scenario">
              <el-form v-if="scenarioForm" label-width="100px">
                <el-form-item label="场景数据">
                  <el-input v-model="scenarioDataStr" type="textarea" :rows="8" placeholder="场景参数 JSON" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" size="small" :loading="paramsSaving" @click="saveScenarioParams">保存场景参数</el-button>
                  <el-button size="small" class="ml-2" @click="formatScenarioJSON">格式化 JSON</el-button>
                </el-form-item>
              </el-form>
              <div v-else class="text-center text-gray-400 py-4">加载中...</div>
            </el-tab-pane>

            <!-- 属性页 -->
            <el-tab-pane label="属性页" name="property">
              <div v-if="propertyForm !== null">
                <div
                  v-for="(entry, idx) in propEntries"
                  :key="entry.key"
                  class="flex items-center gap-2 py-1"
                  style="border-bottom:1px solid #f0f0f0"
                >
                  <span class="param-key-text">{{ entry.key }}</span>
                  <el-input v-model="entry.value" size="small" style="flex:1" />
                  <el-button size="small" type="danger" link @click="removePropEntry(idx)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
                <div class="flex items-center gap-2 mt-2">
                  <el-input v-model="newPropKey" placeholder="输入新键名" size="small" style="width:140px" />
                  <el-input v-model="newPropVal" placeholder="输入新值" size="small" style="flex:1" />
                  <el-button size="small" @click="addPropEntry">添加</el-button>
                  <el-button type="primary" size="small" :loading="paramsSaving" @click="savePropertyParams">保存</el-button>
                </div>
              </div>
              <div v-else class="text-center text-gray-400 py-4">加载中...</div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </div>

    <!-- Context Menu Overlay -->
    <teleport to="body">
      <div v-if="ctxVisible" class="ctx-overlay" @click="closeCtx" @contextmenu.prevent="closeCtx" />
      <div v-if="ctxVisible" class="ctx-menu" :style="ctxStyle">
        <div class="ctx-title">{{ ctxTitle }}</div>
        <div class="ctx-items">
          <template v-for="item in ctxItems" :key="item.label">
            <div v-if="item.divider" class="ctx-divider" />
            <div v-else-if="item.disabled" class="ctx-item ctx-disabled">{{ item.label }}</div>
            <div v-else class="ctx-item" :class="{ 'ctx-danger': item.danger }" @click="execCtx(item)">{{ item.label }}</div>
          </template>
        </div>
      </div>
    </teleport>

    <!-- Scan Dialog -->
    <el-dialog v-model="scanVisible" title="扫码测试" width="400px" :close-on-click-modal="false" destroy-on-close>
      <el-input ref="scanInputRef" v-model="scanBarcode" placeholder="扫描或输入条码..." size="large" @keyup.enter="submitScan" />
      <div v-if="scanTesting" class="scan-progress">
        <el-progress :percentage="scanProgress" :stroke-width="6" />
        <p class="scan-status">{{ scanStatusText }}</p>
      </div>
      <template #footer>
        <el-button @click="scanVisible = false">取消</el-button>
        <el-button type="primary" :loading="scanTesting" @click="submitScan">开始测试</el-button>
      </template>
    </el-dialog>

    <!-- Hardware Param Edit Dialog -->
    <el-dialog v-model="hwDialogVisible" :title="hwDialogEdit ? '编辑硬件参数' : '新建硬件参数'" width="460px" append-to-body destroy-on-close>
      <el-form :model="hwForm" label-width="100px">
        <el-form-item label="参数名">
          <el-input v-model="hwForm.param_name" />
        </el-form-item>
        <el-form-item label="参数值">
          <el-input v-model="hwForm.param_value" />
        </el-form-item>
        <el-form-item label="分组">
          <el-input v-model="hwForm.group_name" placeholder="default" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="hwForm.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="hwDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="paramsSaving" @click="submitHwForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- Cabinet Params Dialog -->
    <el-dialog v-model="cabinetParamsVisible" title="机柜参数设置" width="560px" append-to-body destroy-on-close>
      <div style="margin-bottom: 12px; text-align: right;">
        <el-button type="primary" size="small" @click="addCabinetParam">添加参数</el-button>
      </div>
      <el-table :data="cabinetParamsList" border size="small" max-height="400">
        <el-table-column prop="param_name" label="参数名" />
        <el-table-column prop="param_value" label="参数值" />
        <el-table-column prop="group_name" label="分组" width="100" />
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="editCabinetParam(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="deleteCabinetParamItem(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="cabinetParamsVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- Cabinet Param Edit Dialog -->
    <el-dialog v-model="cabinetParamDialogVisible" :title="cabinetParamDialogEdit ? '编辑参数' : '新建参数'" width="460px" append-to-body destroy-on-close>
      <el-form :model="cabinetParamForm" label-width="100px">
        <el-form-item label="参数名">
          <el-input v-model="cabinetParamForm.param_name" />
        </el-form-item>
        <el-form-item label="参数值">
          <el-input v-model="cabinetParamForm.param_value" />
        </el-form-item>
        <el-form-item label="分组">
          <el-input v-model="cabinetParamForm.group_name" placeholder="default" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="cabinetParamForm.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cabinetParamDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveCabinetParam">保存</el-button>
      </template>
    </el-dialog>

    <!-- Chassis Params Dialog -->
    <el-dialog v-model="chassisParamsVisible" title="机框参数设置" width="560px" append-to-body destroy-on-close>
      <div style="margin-bottom: 12px; text-align: right;">
        <el-button type="primary" size="small" @click="addChassisParam">添加参数</el-button>
      </div>
      <el-table :data="chassisParamsList" border size="small" max-height="400">
        <el-table-column prop="param_name" label="参数名" />
        <el-table-column prop="param_value" label="参数值" />
        <el-table-column prop="group_name" label="分组" width="100" />
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="editChassisParam(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="deleteChassisParamItem(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="chassisParamsVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- Chassis Param Edit Dialog -->
    <el-dialog v-model="chassisParamDialogVisible" :title="chassisParamDialogEdit ? '编辑参数' : '新建参数'" width="460px" append-to-body destroy-on-close>
      <el-form :model="chassisParamForm" label-width="100px">
        <el-form-item label="参数名">
          <el-input v-model="chassisParamForm.param_name" />
        </el-form-item>
        <el-form-item label="参数值">
          <el-input v-model="chassisParamForm.param_value" />
        </el-form-item>
        <el-form-item label="分组">
          <el-input v-model="chassisParamForm.group_name" placeholder="default" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="chassisParamForm.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="chassisParamDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveChassisParam">保存</el-button>
      </template>
    </el-dialog>

    <!-- Batch Replace Dialog -->
    <el-dialog v-model="showBatchReplace" title="批量替换硬件参数" width="560px" append-to-body destroy-on-close>
      <p class="text-sm text-gray-400 mb-2">每行一个，格式：参数名=参数值</p>
      <el-input v-model="batchReplaceText" type="textarea" :rows="8" placeholder="power_voltage=220&#10;current_limit=10&#10;frequency=50" />
      <template #footer>
        <el-button @click="showBatchReplace = false">取消</el-button>
        <el-button type="primary" :loading="batchSaving" @click="submitBatchReplace">替换</el-button>
      </template>
    </el-dialog>

    <!-- Log Panel -->
    <div v-if="showLogPanel" class="log-panel" :style="{ height: logPanelHeight + 'px' }">
        <div class="log-resize-handle" @mousedown="startResize" />
        <div class="log-panel-header">
          <span><span class="log-led" /> 运行日志</span>
          <div class="log-header-actions">
            <span class="log-header-btn" @click="logs = []; localStorage.removeItem(LOG_STORAGE_KEY)">清空</span>
            <span class="log-header-btn" @click="showLogPanel = false">隐藏</span>
          </div>
        </div>
        <div class="log-panel-body-wrapper">
          <div class="log-filter-sidebar">
            <div
              v-for="level in logLevels"
              :key="level.key"
              class="log-filter-item"
              :class="{ active: logFilter === level.key }"
              :style="{ color: level.color, borderLeftColor: logFilter === level.key ? level.color : 'transparent' }"
              @click="logFilter = level.key"
            >
              <span class="filter-label">{{ level.label }}</span>
            </div>
          </div>
          <div class="log-panel-body" ref="logBodyRef">
            <div v-for="(l, i) in filteredLogs" :key="i" class="log-line" :class="'log-' + l.level">
              <span class="log-time">{{ l.time }}</span>
              <span class="log-msg">{{ l.message }}</span>
            </div>
            <div v-if="logs.length === 0" class="log-empty">等待测试事件...</div>
          </div>
        </div>
      </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, reactive, watch, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { stationApi } from '@/api/station'
import { versionApi } from '@/api/version'
import { testApi } from '@/api/test'
import { useWebSocket } from '@/composables/useWebSocket'
import { slotStatusLabel } from '@/utils'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Setting, Memo, FolderOpened, Loading, Refresh, Delete, Close } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
let stationId = Number(route.params.id)

const loading = ref(true)
const detailError = ref('')
const station = ref<any>(null)
const cabinets = ref<any[]>([])
const equipIP = ref('-')
const LOG_STORAGE_KEY = `station_logs_${stationId}`
const logs = ref<Array<{ time: string; level: string; message: string }>>(
  JSON.parse(localStorage.getItem(LOG_STORAGE_KEY) || '[]')
)
const currentBarcode = ref('')
const currentSlotInfo = ref('')
const showLogPanel = ref(true)
const logBodyRef = ref<HTMLElement | null>(null)
const logFilter = ref('all')
const scanInputRef = ref<HTMLInputElement | null>(null)

const scanVisible = ref(false)
const scanBarcode = ref('')
const scanSelectedSlot = ref<any>(null)
const scanTesting = ref(false)
const scanProgress = ref(0)
const scanStatusText = ref('')

const paramsVisible = ref(false)
const paramsTitle = ref('参数设置')
const paramsTab = ref('equipment')
const paramsLoading = ref(false)
const paramsSaving = ref(false)

// Equipment config
const equipForm = ref<any>(null)

// Hardware params
const hwList = ref<any[]>([])
const showBatchReplace = ref(false)
const batchReplaceText = ref('')
const batchSaving = ref(false)
const hwDialogVisible = ref(false)
const hwDialogEdit = ref(false)
const hwDialogId = ref(0)
const hwForm = reactive({ param_name: '', param_value: '', group_name: 'default', sort_order: 0 })

// Cabinet params
const cabinetParamsVisible = ref(false)
const cabinetParamsCabinetId = ref(0)
const cabinetParamsList = ref<any[]>([])
const cabinetParamDialogVisible = ref(false)
const cabinetParamDialogEdit = ref(false)
const cabinetParamDialogId = ref(0)
const cabinetParamForm = reactive({ param_name: '', param_value: '', group_name: 'default', sort_order: 0 })

// Chassis params
const chassisParamsVisible = ref(false)
const chassisParamsChassisId = ref(0)
const chassisParamsList = ref<any[]>([])
const chassisParamDialogVisible = ref(false)
const chassisParamDialogEdit = ref(false)
const chassisParamDialogId = ref(0)
const chassisParamForm = reactive({ param_name: '', param_value: '', group_name: 'default', sort_order: 0 })

// Software config + version cascade
const softForm = ref<any>(null)
const testItems = ref<any[]>([])
const sequences = ref<any[]>([])
const seqDataStr = ref('')

// Version 3-level cascade
const deployedVersions = ref<any[]>([])
const selectedVersionId = ref<number | null>(null)
const selectedVersionBom = ref('')
const selectedBoms = ref('')
const selectedVersionTps = ref('')
const subScenarios = ref<any[]>([])
const selectedSubScenarioId = ref<number | null>(null)
const selectedSubScenario = ref<any>(null)
const sequenceSteps = ref<any[]>([])
const stepCheckMap = ref<Record<number, boolean>>({})

const bomOptions = computed(() => {
  return selectedVersionBom.value
    ? selectedVersionBom.value.split(/[,;，；]/).map((s: string) => s.trim()).filter(Boolean)
    : []
})

async function loadDeployedVersions() {
  try {
    const res = await stationApi.listDeployedVersions(stationId, true)
    deployedVersions.value = res.data || []
  } catch { deployedVersions.value = [] }
}

function onVersionChange(versionId: number) {
  selectedSubScenarioId.value = null
  selectedSubScenario.value = null
  selectedVersionBom.value = ''
  selectedBoms.value = ''
  selectedVersionTps.value = ''
  subScenarios.value = []
  selectedVersionId.value = versionId
  localStorage.setItem(`station_${stationId}_version_id`, String(versionId))
  localStorage.removeItem(`station_${stationId}_sub_scenario_id`)
  const ver = deployedVersions.value.find((v) => v.version_id === versionId)
  if (ver) {
    selectedVersionBom.value = ver.bom_code || ''
    selectedBoms.value = bomOptions.value[0] || ''
    selectedVersionTps.value = ver.tps_name || ''
    let subs = ver.sub_scenarios || []
    // standard 类型版本无子场景时，从 sequence_data 生成默认子场景
    if (!subs.length && softForm.value?.sequence_data && Array.isArray(softForm.value.sequence_data) && softForm.value.sequence_data.length) {
      subs = [{
        id: 0,
        name: '默认测试流程',
        process_type: softForm.value.process_type || '',
        workstation: softForm.value.workstation || '',
        sequence_id: softForm.value.sequence_id || 0,
        bom_snapshot: []
      }]
    }
    subScenarios.value = subs
    softForm.value.project_name = ver.project_name || softForm.value?.project_name || ''
    softForm.value.dut_version = ver.version || softForm.value?.dut_version || ''
    localStorage.setItem(`station_${stationId}_version_context`, JSON.stringify({
      version_id: ver.version_id,
      version: ver.version,
      project_name: ver.project_name,
      bom_code: ver.bom_code,
      tps_name: ver.tps_name,
      sub_scenarios: subs
    }))
  }
}

function loadSubScenarios() {
  if (selectedVersionId.value) onVersionChange(selectedVersionId.value)
}

function onSubScenarioChange(ssId: number) {
  const ss = subScenarios.value.find((s) => s.id === ssId)
  selectedSubScenario.value = ss
  selectedSubScenarioId.value = ssId
  localStorage.setItem(`station_${stationId}_sub_scenario_id`, String(ssId))
  const ver = deployedVersions.value.find((v) => v.version_id === selectedVersionId.value)
  if (ss && ver) {
    localStorage.setItem(`station_${stationId}_sub_scenario_context`, JSON.stringify({
      sub_scenario_id: ss.id,
      sub_scenario_name: ss.name,
      process_type: ss.process_type,
      workstation: ss.workstation,
      sequence_id: ss.sequence_id,
      version_id: ver.version_id,
      version: ver.version,
      project_name: ver.project_name,
      bom_code: ver.bom_code,
      tps_name: ver.tps_name,
      test_items: sequenceSteps.value.map(s => ({
        test_item_id: s.test_item_id || s.id,
        test_item_name: s.test_item_name || s.template_name,
        step_order: s.step_order,
        is_critical: s.is_critical || s.template_is_critical,
        block_type: s.block_type,
        test_type: s.test_type || s.template_category,
        service_address: s.service_address
      }))
    }))
  }
  sequenceSteps.value = []
  stepCheckMap.value = {}
  if (ss) {
    softForm.value.sequence_id = ss.sequence_id || softForm.value?.sequence_id
    if (ss.sequence_id && ss.id !== 0) {
      testApi.getSequence(ss.sequence_id).then((res: any) => {
        const steps = res.data?.steps || []
        sequenceSteps.value = steps
        const map: Record<number, boolean> = {}
        steps.forEach((s: any) => { map[s.id] = true })
        stepCheckMap.value = map
      }).catch(() => {})
    } else if (softForm.value?.sequence_data && Array.isArray(softForm.value.sequence_data)) {
      // 默认子场景(id=0)或无 process_name 过滤时，显示全部 sequence_data
      let filtered = softForm.value.sequence_data
      if (ss.process_type || ss.workstation) {
        filtered = filtered.filter((step: any) =>
          (!ss.process_type || step.process_name === ss.process_type) &&
          (!ss.workstation || step.station_name === ss.workstation)
        )
      }
      sequenceSteps.value = filtered
      const map: Record<number, boolean> = {}
      filtered.forEach((s: any) => { map[s.test_item_id || s.template_id] = true })
      stepCheckMap.value = map
    }
  }
}

// Scenario config
const scenarioForm = ref<any>(null)
const scenarioDataStr = ref('')

// Property page
const propertyForm = ref<any>(null)
const propEntries = ref<{ key: string; value: string }[]>([])

const ctxVisible = ref(false)
const ctxItems = ref<any[]>([])
const ctxTitle = ref('')
const ctxStyle = ref({ left: '0px', top: '0px' })
let ctxCallback: (() => void) | null = null

const { connected: wsConnected, connect: wsConnect, disconnect: wsDisconnect, on: wsOn, off: wsOff } = useWebSocket(stationId)

const filteredLogs = computed(() => {
  if (logFilter.value === 'all') return logs.value
  return logs.value.filter((l) => l.level === logFilter.value)
})

const logLevels = computed(() => [
  { key: 'all', label: '全部', color: '#90a4ae' },
  { key: 'info', label: '信息', color: '#42a5f5' },
  { key: 'warn', label: '警告', color: '#ffc107' },
  { key: 'error', label: '错误', color: '#ef5350' },
])

const currentVersionLabel = computed(() => {
  if (!selectedVersionId.value) return ''
  const v = deployedVersions.value.find((d) => d.version_id === selectedVersionId.value)
  return v ? `${v.project_name} v${v.version}` : ''
})

const logPanelHeight = ref(200)
let resizeState: { startY: number; startH: number } | null = null

function startResize(e: MouseEvent) {
  resizeState = { startY: e.clientY, startH: logPanelHeight.value }
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  e.preventDefault()
}
function onResize(e: MouseEvent) {
  if (!resizeState) return
  const dy = resizeState.startY - e.clientY
  logPanelHeight.value = Math.max(80, resizeState.startH + dy)
}
function stopResize() {
  resizeState = null
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
}

function addLog(level: string, message: string) {
  const now = new Date()
  const time = now.toLocaleString('zh-CN', { hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
  logs.value.push({ time, level, message })
  if (logs.value.length > 500) logs.value.shift()
  localStorage.setItem(LOG_STORAGE_KEY, JSON.stringify(logs.value))
  nextTick(() => {
    if (logBodyRef.value) logBodyRef.value.scrollTop = logBodyRef.value.scrollHeight
  })
}

function findSlotLocation(slotId: number): string {
  for (const cab of cabinets.value) {
    for (const ch of (cab.chassis_list || [])) {
      for (const sl of (ch.slots || [])) {
        if (sl.id === slotId) {
          return `${cab.name || '柜'}/${ch.name || '框'}/S${sl.sort_order + 1}`
        }
      }
    }
  }
  return ''
}

function updateLocalSlot(slotId: number, updates: Record<string, any>) {
  for (const cab of cabinets.value) {
    for (const ch of (cab.chassis_list || [])) {
      for (const sl of (ch.slots || [])) {
        if (sl.id === slotId) {
          Object.assign(sl, updates)
          return
        }
      }
    }
  }
}

async function loadFullDetail() {
  loading.value = true
  detailError.value = ''
  try {
    const [detailRes, softRes] = await Promise.all([
      stationApi.getStationDetail(stationId),
      stationApi.getSoftware(stationId),
    ])
    const detail = detailRes.data
    if (!detail) { detailError.value = '装备不存在'; return }
    station.value = detail.station
    cabinets.value = detail.cabinets || []

    const cfg = await stationApi.getEquipment(stationId).catch(() => null)
    if (cfg?.data) {
      equipIP.value = cfg.data.equipment_ip || '-'
      addLog('info', `装备 IP: ${cfg.data.equipment_ip || '-'}`)
      addLog('info', `条码校验: ${cfg.data.barcode_verify_enabled ? '开启' : '关闭'}`)
      addLog('info', `调试模式: ${cfg.data.debug_mode_enabled ? '开启' : '关闭'}`)
    }
  } catch (e: any) {
    detailError.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

/* Lightweight refresh: only update slot status locally, no full API reload */
function updateLocalSlotStatus(slotId: number, status: string) {
  for (const cab of cabinets.value) {
    for (const ch of cab.chassis_list) {
      const slot = ch.slots.find((s: any) => s.id === slotId)
      if (slot) { slot.status = status; return }
    }
  }
}

function selectSlot(slot: any) { /* click feedback handled by CSS */ }

// ── Context Menu ──
function showCtx(event: MouseEvent, title: string, items: any[], cb?: () => void) {
  ctxTitle.value = title
  ctxItems.value = items
  ctxCallback = cb || null
  let x = event.clientX, y = event.clientY
  const mw = 220, mh = items.length * 34 + 40
  if (x + mw > window.innerWidth) x = window.innerWidth - mw - 10
  if (y + mh > window.innerHeight) y = window.innerHeight - mh - 10
  ctxStyle.value = { left: x + 'px', top: y + 'px' }
  ctxVisible.value = true
}

function closeCtx() { ctxVisible.value = false; ctxItems.value = []; ctxCallback = null }

function execCtx(item: any) {
  if (item.fn) item.fn()
  closeCtx()
}

function showStationMenu(event: MouseEvent, id: number) {
  showCtx(event, station.value?.name || '测试工站', [
    { label: '运行日志', fn: () => router.push('/logs') },
    { label: '切换账号', fn: () => router.push('/login') },
    { label: '参数设置', fn: () => { closeCtx(); openParamsPanel() } },
  ])
}

function showCabinetMenu(event: MouseEvent, cab: any) {
  showCtx(event, cab.name, [
    { label: '强制重启', fn: () => forceRestartCabinet(cab.id) },
    { label: '机柜参数', fn: () => { closeCtx(); showCabinetParams(cab.id) } },
  ])
}

function showChassisMenu(event: MouseEvent, ch: any) {
  showCtx(event, ch.name, [
    { label: '强制重启', fn: () => forceRestartChassis(ch.id) },
    { label: '禁用所有槽位', fn: () => toggleAllSlots(ch.id, false) },
    { label: '启用所有槽位', fn: () => toggleAllSlots(ch.id, true) },
    { label: '机框参数', fn: () => { closeCtx(); showChassisParams(ch.id) } },
  ])
}

function showSlotMenu(event: MouseEvent, slot: any, ch: any) {
  const items: any[] = [
    { label: '开始测试', fn: () => { closeCtx(); openScanDialog(slot) } },
  ]
  if (slot.status !== 'idle') {
    items.push({ label: '强制重启', fn: () => forceRestartSlot(slot) })
  }
  if (slot.status === 'idle' || slot.status === 'fail') {
    items.push({ label: '标记通过', fn: () => updateSlotStatus(slot.id, 'pass') })
    items.push({ label: '标记失败', fn: () => updateSlotStatus(slot.id, 'fail') })
  }
  if (slot.status === 'pass' || slot.status === 'fail') {
    items.push({ label: '重置空闲', fn: () => updateSlotStatus(slot.id, 'idle') })
  }
  items.push(
    { label: '禁用槽位', fn: () => updateSlotStatus(slot.id, 'disabled') },
    { label: '启用槽位', fn: () => updateSlotStatus(slot.id, 'idle') },
  )
  showCtx(event, slot.name.replace('槽位 ', 'S'), items)
}

// ── Parameters ──
async function openParamsPanel() {
  if (paramsVisible.value) { paramsVisible.value = false; return }
  paramsVisible.value = true
  await showStationParams()
}

async function showStationParams() {
  paramsTitle.value = '参数设置 — ' + (station.value?.name || '')
  paramsTab.value = 'equipment'
  paramsLoading.value = true
  equipForm.value = null; softForm.value = null; scenarioForm.value = null
  hwList.value = []; testItems.value = []; sequences.value = []
  // Preserve version cascade state across dialog reopen
  const prevVersionId = selectedVersionId.value
  const prevSubScenarioId = selectedSubScenarioId.value
  try {
    const [eqRes, swRes, scRes, ppRes, hwRes, itemsRes, seqRes, depRes] = await Promise.all([
      stationApi.getEquipment(stationId).catch(() => ({ data: null })),
      stationApi.getSoftware(stationId).catch(() => ({ data: null })),
      stationApi.getScenario(stationId).catch(() => ({ data: null })),
      stationApi.getPropertyPage(stationId).catch(() => ({ data: null })),
      stationApi.listHardware(stationId).catch(() => ({ data: [] })),
      testApi.listItems().catch(() => ({ data: [] })),
      testApi.listSequences().catch(() => ({ data: [] })),
      stationApi.listDeployedVersions(stationId, true).catch(() => ({ data: [] })),
    ])
    equipForm.value = eqRes.data || {}
    softForm.value = swRes.data || {}
    seqDataStr.value = softForm.value?.sequence_data ? JSON.stringify(softForm.value.sequence_data, null, 2) : ''
    scenarioForm.value = scRes.data || {}
    scenarioDataStr.value = scenarioForm.value?.scenario_data ? JSON.stringify(scenarioForm.value.scenario_data, null, 2) : '{}'
    hwList.value = hwRes.data || []
    testItems.value = itemsRes.data || []
    sequences.value = seqRes.data || []
    deployedVersions.value = depRes.data || []
    // Load property page as key-value entries
    const pp = ppRes.data?.page_data || {}
    propertyForm.value = pp
    propEntries.value = Object.entries(pp).map(([k, v]) => ({ key: k, value: String(v ?? '') }))
    // Restore version cascade if previously selected version is still valid
    if (prevVersionId && deployedVersions.value.some((v: any) => v.version_id === prevVersionId)) {
      selectedVersionId.value = prevVersionId
      onVersionChange(prevVersionId)
      if (prevSubScenarioId && subScenarios.value.some((s: any) => s.id === prevSubScenarioId)) {
        selectedSubScenarioId.value = prevSubScenarioId
        onSubScenarioChange(prevSubScenarioId)
      }
    } else {
      selectedVersionId.value = null
      selectedSubScenarioId.value = null
      selectedSubScenario.value = null
      selectedVersionBom.value = ''
      selectedVersionTps.value = ''
      subScenarios.value = []
    }
  } catch { /* partial load ok */ }
  paramsLoading.value = false
}

async function showCabinetParams(id: number) {
  cabinetParamsCabinetId.value = id
  cabinetParamsVisible.value = true
  try {
    const res = await stationApi.listCabinetParams(id)
    cabinetParamsList.value = res.data || []
  } catch { cabinetParamsList.value = [] }
}

function addCabinetParam() {
  cabinetParamDialogEdit.value = false
  cabinetParamDialogId.value = 0
  Object.assign(cabinetParamForm, { param_name: '', param_value: '', group_name: 'default', sort_order: 0 })
  cabinetParamDialogVisible.value = true
}

function editCabinetParam(row: any) {
  cabinetParamDialogEdit.value = true
  cabinetParamDialogId.value = row.id
  Object.assign(cabinetParamForm, { param_name: row.param_name, param_value: row.param_value, group_name: row.group_name, sort_order: row.sort_order })
  cabinetParamDialogVisible.value = true
}

async function saveCabinetParam() {
  try {
    if (cabinetParamDialogEdit.value) {
      await stationApi.updateCabinetParam(cabinetParamDialogId.value, { ...cabinetParamForm })
    } else {
      await stationApi.createCabinetParam(cabinetParamsCabinetId.value, { ...cabinetParamForm })
    }
    cabinetParamDialogVisible.value = false
    showCabinetParams(cabinetParamsCabinetId.value)
    ElMessage.success('保存成功')
  } catch { /* empty */ }
}

async function deleteCabinetParamItem(id: number) {
  try {
    await stationApi.deleteCabinetParam(id)
    showCabinetParams(cabinetParamsCabinetId.value)
    ElMessage.success('删除成功')
  } catch { /* empty */ }
}

async function showChassisParams(id: number) {
  chassisParamsChassisId.value = id
  chassisParamsVisible.value = true
  try {
    const res = await stationApi.listChassisParams(id)
    chassisParamsList.value = res.data || []
  } catch { chassisParamsList.value = [] }
}

function addChassisParam() {
  chassisParamDialogEdit.value = false
  chassisParamDialogId.value = 0
  Object.assign(chassisParamForm, { param_name: '', param_value: '', group_name: 'default', sort_order: 0 })
  chassisParamDialogVisible.value = true
}

function editChassisParam(row: any) {
  chassisParamDialogEdit.value = true
  chassisParamDialogId.value = row.id
  Object.assign(chassisParamForm, { param_name: row.param_name, param_value: row.param_value, group_name: row.group_name, sort_order: row.sort_order })
  chassisParamDialogVisible.value = true
}

async function saveChassisParam() {
  try {
    if (chassisParamDialogEdit.value) {
      await stationApi.updateChassisParam(chassisParamDialogId.value, { ...chassisParamForm })
    } else {
      await stationApi.createChassisParam(chassisParamsChassisId.value, { ...chassisParamForm })
    }
    chassisParamDialogVisible.value = false
    showChassisParams(chassisParamsChassisId.value)
    ElMessage.success('保存成功')
  } catch { /* empty */ }
}

async function deleteChassisParamItem(id: number) {
  try {
    await stationApi.deleteChassisParam(id)
    showChassisParams(chassisParamsChassisId.value)
    ElMessage.success('删除成功')
  } catch { /* empty */ }
}

// ── Equipment params ──
async function saveEquipParams() {
  paramsSaving.value = true
  try {
    await stationApi.updateEquipment(stationId, equipForm.value)
    equipIP.value = equipForm.value?.equipment_ip || '-'
    ElMessage.success('装备参数保存成功')
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    paramsSaving.value = false
  }
}

// ── Hardware params ──
function openHwDialog(row?: any) {
  if (row) {
    hwDialogEdit.value = true; hwDialogId.value = row.id
    Object.assign(hwForm, { param_name: row.param_name, param_value: row.param_value, group_name: row.group_name, sort_order: row.sort_order })
  } else {
    hwDialogEdit.value = false; hwDialogId.value = 0
    Object.assign(hwForm, { param_name: '', param_value: '', group_name: 'default', sort_order: 0 })
  }
  hwDialogVisible.value = true
}

async function submitHwForm() {
  paramsSaving.value = true
  try {
    if (hwDialogEdit.value) {
      await stationApi.updateHardware(hwDialogId.value, hwForm)
    } else {
      await stationApi.createHardware(stationId, hwForm)
    }
    ElMessage.success('硬件参数保存成功')
    hwDialogVisible.value = false
    hwList.value = (await stationApi.listHardware(stationId).catch(() => ({ data: [] }))).data || []
  } catch (e: any) {
    ElMessage.error(e?.message || '操作失败')
  } finally {
    paramsSaving.value = false
  }
}

async function deleteHw(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除参数 "${row.param_name}"？`, '确认')
    await stationApi.deleteHardware(row.id)
    ElMessage.success('已删除')
    hwList.value = (await stationApi.listHardware(stationId).catch(() => ({ data: [] }))).data || []
  } catch { /* cancelled */ }
}

async function refreshHardware() {
  paramsSaving.value = true
  try {
    hwList.value = (await stationApi.listHardware(stationId).catch(() => ({ data: [] }))).data || []
    ElMessage.success('硬件参数已刷新')
  } catch { /* ok */ } finally {
    paramsSaving.value = false
  }
}

async function submitBatchReplace() {
  batchSaving.value = true
  try {
    const lines = batchReplaceText.value.split('\n').filter(Boolean)
    const params = lines.map((line: string) => {
      const [n, ...vs] = line.split('=')
      return { param_name: n.trim(), param_value: vs.join('=').trim(), group_name: 'default', sort_order: 0 }
    })
    await stationApi.batchReplaceHardware(stationId, { params })
    ElMessage.success(`批量替换成功，共 ${params.length} 条`)
    showBatchReplace.value = false
    batchReplaceText.value = ''
    hwList.value = (await stationApi.listHardware(stationId).catch(() => ({ data: [] }))).data || []
  } catch (e: any) {
    ElMessage.error(e?.message || '批量替换失败')
  } finally {
    batchSaving.value = false
  }
}

// ── Software params ──
async function saveSoftParams() {
  paramsSaving.value = true
  try {
    const data = { ...softForm.value }
    if (seqDataStr.value) {
      try { data.sequence_data = JSON.parse(seqDataStr.value) }
      catch { data.sequence_data = seqDataStr.value }
    }
    await stationApi.updateSoftware(stationId, data)
    // Sync version product properties to station property page
    if (selectedVersionId.value) {
      await stationApi.syncVersionProps(stationId, { version_id: selectedVersionId.value })
      const ppRes = await stationApi.getPropertyPage(stationId)
      const pp = ppRes.data?.page_data || {}
      propertyForm.value = pp
      propEntries.value = Object.entries(pp).map(([k, v]) => ({ key: k, value: String(v ?? '') }))
    }
    ElMessage.success('软件参数保存成功')
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    paramsSaving.value = false
  }
}

// ── Scenario params ──
function formatScenarioJSON() {
  try { scenarioDataStr.value = JSON.stringify(JSON.parse(scenarioDataStr.value), null, 2) }
  catch { ElMessage.warning('JSON 格式无效') }
}

async function saveScenarioParams() {
  paramsSaving.value = true
  try {
    let data: any
    try { data = JSON.parse(scenarioDataStr.value) }
    catch { data = scenarioDataStr.value }
    await stationApi.updateScenario(stationId, { scenario_data: data })
    ElMessage.success('场景参数保存成功')
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    paramsSaving.value = false
  }
}

// ── Property page ──
const newPropKey = ref('')
const newPropVal = ref('')

function removePropEntry(idx: number) {
  propEntries.value.splice(idx, 1)
}

function addPropEntry() {
  const k = newPropKey.value.trim()
  if (!k) { ElMessage.warning('请输入键名'); return }
  if (propEntries.value.some(e => e.key === k)) { ElMessage.warning('键名已存在'); return }
  propEntries.value.push({ key: k, value: newPropVal.value })
  newPropKey.value = ''
  newPropVal.value = ''
}

async function savePropertyParams() {
  paramsSaving.value = true
  try {
    const page_data: Record<string, string> = {}
    for (const e of propEntries.value) {
      if (e.key.trim()) page_data[e.key.trim()] = e.value
    }
    await stationApi.updatePropertyPage(stationId, { page_data })
    propertyForm.value = page_data
    ElMessage.success('属性页保存成功')
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    paramsSaving.value = false
  }
}

// ── Slot Actions ──
async function updateSlotStatus(slotId: number, status: string) {
  try {
    await stationApi.updateSlot(slotId, { status })
    updateLocalSlotStatus(slotId, status)
    addLog('info', `槽位 ${slotId} → ${status}`)
    ElMessage.success('状态更新成功')
  } catch (e: any) {
    ElMessage.error(e?.message || '更新失败')
  }
}

async function toggleAllSlots(chassisId: number, enable: boolean) {
  const status = enable ? 'idle' : 'disabled'
  const action = enable ? '启用' : '禁用'
  for (const cab of cabinets.value) {
    for (const ch of cab.chassis_list) {
      if (ch.id !== chassisId) continue
      for (const slot of ch.slots) {
        try {
          await stationApi.updateSlot(slot.id, { status })
          slot.status = status
        } catch { /* skip individual failure */ }
      }
    }
  }
  addLog('info', `${action}机框 ${chassisId} 所有槽位`)
  ElMessage.success(`${action}成功`)
}

async function forceRestartStation(id: number) {
  addLog('warn', `强制重启工站 ${id}`)
  ElMessage.success('重启指令已发送（需后端接口支持）')
}

async function forceRestartSlot(slot: any) {
  try {
    const res = await stationApi.forceRestartSlot(slot.id)
    const info = res.data
    if (info?.reset) {
      addLog('warn', `强制重启槽位 ${info?.slot_name || slot.name}，状态 ${info?.old_status} → idle`)
    } else {
      addLog('info', `槽位 ${info?.slot_name || slot.name} 已是空闲，无需重置`)
    }
    ElMessage.success('槽位已重置')
    await loadFullDetail()
  } catch (e: any) {
    ElMessage.error(e?.message || '重启失败')
  }
}

async function forceRestartCabinet(id: number) {
  try {
    const res = await stationApi.forceRestartCabinet(id)
    const info = res.data
    const count = info?.reset_count ?? 0
    const details = (info?.chassis || []).map((ch: any) =>
      `${ch.chassis_name}(${ch.slot_names.join(',')})`
    ).join('、')
    addLog('warn', `强制重启机柜 ${info?.cabinet_name || id}，已重置 ${count} 个槽位: ${details}`)
    ElMessage.success(`已重置 ${count} 个槽位`)
    await loadFullDetail()
  } catch (e: any) {
    ElMessage.error(e?.message || '重启失败')
  }
}

async function forceRestartChassis(id: number) {
  try {
    const res = await stationApi.forceRestartChassis(id)
    const info = res.data
    const count = info?.reset_count ?? 0
    const slotNames = (info?.slot_names || []).join(',')
    addLog('warn', `强制重启机框 ${info?.chassis_name || id}，已重置 ${count} 个槽位: ${slotNames}`)
    ElMessage.success(`已重置 ${count} 个槽位`)
    await loadFullDetail()
  } catch (e: any) {
    ElMessage.error(e?.message || '重启失败')
  }
}

// ── Scan ──
function openScanDialog(slot: any) {
  if (slot.status === 'testing') {
    ElMessage.warning('该槽位正在测试中，不允许再次输入条码')
    return
  }
  scanSelectedSlot.value = slot
  scanBarcode.value = ''
  scanProgress.value = 0
  scanTesting.value = false
  scanStatusText.value = ''
  scanVisible.value = true
  nextTick(() => scanInputRef.value?.focus?.())
}

async function submitScan() {
  if (!scanBarcode.value.trim()) { ElMessage.warning('请输入条码'); return }
  if (scanSelectedSlot.value?.status === 'testing') {
    ElMessage.warning('该槽位正在测试中，不允许再次输入条码')
    return
  }
  scanTesting.value = true
  scanStatusText.value = '启动中...'
  try {
    const run = await testApi.scanTest({
      serial_number: scanBarcode.value.trim(),
      slot_id: scanSelectedSlot.value.id,
      station_id: stationId,
    })
    updateLocalSlot(scanSelectedSlot.value.id, {
      status: 'testing',
      current_batch_id: run.data?.batch_id || null,
      serial_number: scanBarcode.value.trim(),
    })
    addLog('info', `[创建] 条码: ${scanBarcode.value.trim()} | 批次: ${run.data?.batch_id || '-'} | 槽位: ${findSlotLocation(scanSelectedSlot.value.id) || '-'}`)
    scanVisible.value = false
  } catch (e: any) {
    addLog('error', `测试启动失败: ${e?.message || ''}`)
    ElMessage.error(e?.message || '测试启动失败')
  } finally {
    scanTesting.value = false
  }
}

function downloadFile(file: any) {
  const url = versionApi.downloadBinaryUrl(selectedVersionId.value!, file.id)
  window.open(url, '_blank')
  addLog('info', `下载文件: ${file.filename}`)
}

// ── Lifecycle ──
const wsHandlers: Array<{ event: string; handler: (msg: any) => void }> = []

function restoreSelections() {
  const versionCtx = localStorage.getItem(`station_${stationId}_version_context`)
  const subScenarioCtx = localStorage.getItem(`station_${stationId}_sub_scenario_context`)
  if (versionCtx) {
    try {
      const ctx = JSON.parse(versionCtx)
      const ver = deployedVersions.value.find((v) => v.version_id === ctx.version_id)
      if (ver) {
        selectedVersionId.value = ctx.version_id
        onVersionChange(ctx.version_id)
        if (subScenarioCtx) {
          try {
            const ssCtx = JSON.parse(subScenarioCtx)
            if (ssCtx.version_id === ctx.version_id) {
              // 先从 ver.sub_scenarios 找，再从 subScenarios.value 找（含默认子场景）
              let ss = ver.sub_scenarios?.find((s: any) => s.id === ssCtx.sub_scenario_id)
              if (!ss) ss = subScenarios.value.find((s: any) => s.id === ssCtx.sub_scenario_id)
              if (ss) {
                selectedSubScenarioId.value = ssCtx.sub_scenario_id
                selectedSubScenario.value = ss
                onSubScenarioChange(ssCtx.sub_scenario_id)
                if (ssCtx.test_items && ssCtx.test_items.length) {
                  ssCtx.test_items.forEach((ti: any) => {
                    stepCheckMap.value[ti.test_item_id] = true
                  })
                }
              }
            }
          } catch {}
        }
      }
    } catch {}
  }
}

onMounted(() => {
  loadFullDetail()
  loadDeployedVersions().then(restoreSelections)
  wsConnect()
  const h1 = (msg: any) => {
    const d = msg.data || {}
    currentBarcode.value = d.serial_number || ''
    currentSlotInfo.value = d.slot_id ? findSlotLocation(d.slot_id) : ''
    if (d.slot_id) {
      updateLocalSlot(d.slot_id, { status: 'testing', current_batch_id: d.batch_id, serial_number: d.serial_number })
    }
    addLog('info', `[开始] 条码: ${d.serial_number || '-'} | 批次: ${d.batch_id || '-'} | 槽位: ${currentSlotInfo.value || '-'}`)
  }
  const h2 = (msg: any) => {
    const d = msg.data
    const barcode = currentBarcode.value
    const loc = currentSlotInfo.value
    addLog(d.passed ? 'info' : 'error', `[测试] 条码: ${barcode || '-'} | ${loc || '-'} | ${d.item_name || ''}: ${d.actual_value}${d.passed ? ' ✓' : ' ✗ (期望: ' + d.expected_value + ')'}`)
  }
  const h3 = (msg: any) => {
    const d = msg.data || {}
    if (d.slot_id) {
      updateLocalSlot(d.slot_id, { status: 'pass', current_batch_id: null, serial_number: null })
    }
    addLog('info', `[完成] 条码: ${currentBarcode.value || '-'} | 总计: ${d.total || '-'} | 通过: ${d.passed || 0} | 失败: ${d.failed || 0}`)
    currentBarcode.value = ''
    currentSlotInfo.value = ''
  }
  const h4 = (msg: any) => {
    const d = msg.data || {}
    if (d.slot_id) {
      updateLocalSlot(d.slot_id, { status: 'fail', current_batch_id: null, serial_number: null })
    }
    addLog('error', `[失败] 条码: ${currentBarcode.value || '-'} | 错误: ${d.error || '未知错误'}`)
    currentBarcode.value = ''
    currentSlotInfo.value = ''
  }
  wsOn('run_started', h1); wsHandlers.push({ event: 'run_started', handler: h1 })
  wsOn('item_tested', h2); wsHandlers.push({ event: 'item_tested', handler: h2 })
  wsOn('run_completed', h3); wsHandlers.push({ event: 'run_completed', handler: h3 })
  wsOn('run_failed', h4); wsHandlers.push({ event: 'run_failed', handler: h4 })
  document.addEventListener('click', closeCtx)
})

onActivated(() => {
  const newId = Number(route.params.id)
  if (newId !== stationId) {
    stationId = newId
    wsDisconnect()
    wsHandlers.length = 0
  }
  loadFullDetail()
  loadDeployedVersions().then(restoreSelections)
  if (!wsConnected.value) wsConnect()
})

watch(() => route.params.id, (newId) => {
  if (newId) {
    stationId = Number(newId)
    loadFullDetail()
  }
})

onUnmounted(() => {
  for (const { event, handler } of wsHandlers) wsOff(event, handler)
  document.removeEventListener('click', closeCtx)
  stopResize()
})
</script>

<style scoped>
.station-monitor { padding: 4px 0; color: #e0e0e0;
  display: flex; flex-direction: column; height: 100%; min-height: 0; }

/* Header */
.monitor-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 12px;
  background: linear-gradient(135deg, #1a2332 0%, #243044 100%);
  border: 1px solid #2d4055; border-radius: 8px;
  flex-shrink: 0;
}
.header-left { display: flex; flex-direction: column; gap: 1px; }
.station-title { display: flex; align-items: center; gap: 6px; }
.status-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  transition: background 0.3s;
}
.status-dot.online { background: #00e676; box-shadow: 0 0 4px #00e676; }
.status-dot.offline { background: #ff5252; box-shadow: 0 0 4px #ff5252; }
.station-name { font-size: 1.1rem; font-weight: 700; color: #ffffff; margin: 0; }
.station-badge {
  font-size: 0.65rem; font-weight: 600; text-transform: uppercase;
  color: #64b5f6; background: rgba(100,181,246,0.12);
  padding: 1px 6px; border-radius: 3px;
}
.station-meta { display: flex; gap: 10px; font-size: 0.7rem; color: #809ab3; align-items: center; }
.version-badge {
  font-size: 0.65rem; color: #64b5f6; background: rgba(100,181,246,0.12);
  padding: 0 6px; border-radius: 3px; font-weight: 600;
  white-space: nowrap;
}
.header-right { display: flex; align-items: center; gap: 6px; }
.param-btn { background: #2d4055; border-color: #405570; color: #b0c4de; height: 28px; padding: 0 10px; font-size: 0.75rem; }
.param-btn:hover { background: #405570; color: #fff; }

/* Loading / Error */
.loading-state, .error-state { text-align: center; padding: 30px 0; color: #809ab3; }
.loading-state .is-loading { animation: spin 1s linear infinite; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

/* Equipment View */
.equipment-view {
  background: #0d1b2a;
  border: 1px solid #1b2d3e;
  border-radius: 8px;
  padding: 12px 4px;
  min-height: 200px;
  margin: 10px 0 0;
  flex: 1 1 auto;
  overflow-y: auto;
}
.equipment-view.single-cab .cabinet-row {
  justify-content: center;
}
.equipment-view.single-cab .cabinet-unit {
  max-width: 380px;
  min-height: 360px;
}
.equipment-view.single-cab .slot-grid {
  display: grid;
  gap: 8px;
  flex: 1;
}
.equipment-view.single-cab .slot-cell {
  height: 82px;
}

.empty-cabinets { text-align: center; padding: 40px 0; color: #546e7a; }

/* Cabinet Row */
.cabinet-row { display: flex; gap: 12px; padding: 8px; flex-wrap: wrap; justify-content: center; }
.cabinet-unit {
  background: #112233;
  border: 1px solid #1e3350;
  border-radius: 6px;
  min-width: 200px;
  max-width: 320px;
  min-height: 320px;
  flex: 1 1 auto;
}
.cabinet-unit-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 5px 10px;
  background: linear-gradient(90deg, #1a2d47 0%, #1f3550 100%);
  border-bottom: 1px solid #1e3350;
  cursor: default;
}
.cabinet-unit-name { font-weight: 700; font-size: 0.82rem; color: #b0c4de; }
.cabinet-param-link { color: #546e7a; cursor: pointer; font-size: 0.78rem; }
.cabinet-param-link:hover { color: #4fc3f7; }

/* Chassis */
.chassis-list { display: flex; flex-direction: column; gap: 8px; padding: 8px; }
.chassis-unit {
  background: #0a1929;
  border: 1px solid #1a2d47;
  border-radius: 6px;
  padding: 10px;
}
.chassis-unit-header {
  display: flex; align-items: center; gap: 6px;
  margin-bottom: 6px; padding-bottom: 6px;
  border-bottom: 1px solid #1a2d47;
  cursor: default;
}
.chassis-unit-name { font-weight: 600; font-size: 0.82rem; color: #b0c4de; }
.chassis-slot-count { margin-left: auto; font-size: 0.68rem; color: #546e7a; }
.chassis-param-link { color: #546e7a; cursor: pointer; font-size: 0.75rem; }
.chassis-param-link:hover { color: #4fc3f7; }

/* Slot Grid - 固定4列 */
.slot-grid { display: grid; gap: 6px; }
.slot-cell {
  position: relative;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 72px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s;
  overflow: hidden;
  user-select: none;
}
.slot-cell:hover { transform: translateY(-1px); box-shadow: 0 3px 8px rgba(0,0,0,0.4); }

/* Slot LED */
.slot-led {
  position: absolute; top: 4px; left: 4px;
  width: 8px; height: 8px; border-radius: 50%;
}
.led-idle { background: #607d8b; }
.led-testing { background: #2196f3; box-shadow: 0 0 6px #2196f3; animation: blink 0.8s infinite; }
.led-pass { background: #00e676; box-shadow: 0 0 6px #00e676; }
.led-fail { background: #ff1744; box-shadow: 0 0 6px #ff1744; }
.led-disabled { background: #37474f; }

@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

.slot-cell.slot-idle {
  background: #1a2a3a; border: 1px solid #2a3e55; color: #78909c;
}
.slot-cell.slot-idle:hover { border-color: #4fc3f7; }
.slot-cell.slot-testing {
  background: linear-gradient(135deg, #0d253f 0%, #14334f 100%);
  border: 1px solid #1976d2; color: #90caf9;
}
.slot-cell.slot-testing:hover { border-color: #42a5f5; }
.slot-cell.slot-pass {
  background: linear-gradient(135deg, #0d3320 0%, #144028 100%);
  border: 1px solid #2e7d32; color: #81c784;
}
.slot-cell.slot-pass:hover { border-color: #66bb6a; }
.slot-cell.slot-fail {
  background: linear-gradient(135deg, #3a0d14 0%, #4a141f 100%);
  border: 1px solid #c62828; color: #ef9a9a;
}
.slot-cell.slot-fail:hover { border-color: #e53935; }
.slot-cell.slot-disabled {
  background: #121e2c; border: 1px solid #263543; color: #455a64; opacity: 0.6; cursor: default;
}
.slot-name { font-weight: 600; font-size: 0.85rem; line-height: 1.2; }
.slot-status { font-size: 0.65rem; line-height: 1; }
.slot-sn { font-size: 0.6rem; color: #64b5f6; font-weight: 600; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
.slot-batch {
  font-size: 0.55rem; color: #546e7a; max-width: 100%;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* Slot progress bar */
.slot-progress {
  position: absolute; bottom: 0; left: 0; right: 0; height: 3px;
  background: rgba(255,255,255,0.06);
}
.slot-progress-bar {
  height: 100%; transition: width 0.5s ease;
  background: linear-gradient(90deg, #2196f3, #4fc3f7);
  border-radius: 0 2px 0 0;
}
.slot-progress.active .slot-progress-bar {
  background: linear-gradient(90deg, #1976d2, #42a5f5);
  animation: pulse-width 1.5s infinite;
}
@keyframes pulse-width {
  0%, 100% { opacity: 1; } 50% { opacity: 0.4; }
}

/* Context Menu */
.ctx-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 9998;
}
.ctx-menu {
  position: fixed; z-index: 9999;
  background: #1a2332; border: 1px solid #2d4055; border-radius: 6px;
  min-width: 200px; box-shadow: 0 8px 24px rgba(0,0,0,0.5);
  overflow: hidden;
}
.ctx-title {
  padding: 8px 14px; font-size: 0.75rem; font-weight: 600;
  color: #64b5f6; background: #0d1b2a;
  border-bottom: 1px solid #1e3350;
}
.ctx-items { padding: 4px 0; }
.ctx-item {
  padding: 7px 14px; font-size: 0.85rem; cursor: pointer;
  color: #b0c4de; transition: background 0.1s;
}
.ctx-item:hover { background: #1a2d47; color: #e0e0e0; }
.ctx-item.ctx-danger { color: #ef9a9a; }
.ctx-item.ctx-danger:hover { background: #3a0d14; color: #ffcdd2; }
.ctx-disabled { color: #546e7a; font-style: italic; cursor: default; }
.ctx-divider { height: 1px; background: #1e3350; margin: 4px 0; }

/* Scan dialog */
.scan-progress { margin-top: 16px; }
.scan-status { text-align: center; font-size: 0.8rem; color: #809ab3; margin-top: 4px; }

/* Version cascade */
.hw-params-preview { display: flex; flex-wrap: wrap; gap: 4px; }
.version-cascade .el-form-item { margin-bottom: 0; }
.version-cascade .el-form-item__label { font-size: 0.8rem; }
.version-cascade .el-select, .version-cascade .el-input { font-size: 0.85rem; }

/* Version Info Bar */
.version-info-bar {
  display: flex; gap: 16px; align-items: center;
  padding: 3px 12px;
  background: linear-gradient(90deg, #152238 0%, #1a2d47 100%);
  border-bottom: 1px solid #1e3350;
  flex-shrink: 0;
  min-height: 26px;
}
.info-item { display: flex; align-items: center; gap: 4px; }
.info-label { font-size: 0.65rem; color: #64b5f6; font-weight: 600; }
.info-value { font-size: 0.72rem; color: #e0e0e0; font-weight: 700; }

/* Main content flex layout */
.main-content {
  display: flex; flex: 1; min-height: 0; overflow: auto;
}

/* Params Panel - light theme for visual differentiation */
.params-panel {
  width: 480px; min-width: 480px; max-width: 90vw;
  background: #f5f7fa;
  border-left: 1px solid #d9ecff;
  display: flex; flex-direction: column;
  overflow-x: auto;
  flex-shrink: 0;
}
.params-panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 10px;
  background: linear-gradient(90deg, #152238 0%, #1a2d47 100%);
  border-bottom: 1px solid #1e3350;
  flex-shrink: 0;
}
.params-panel-title {
  font-weight: 700; font-size: 0.8rem; color: #e0e0e0;
}
.params-panel-body {
  flex: 1; overflow-y: auto; padding: 10px;
  background: #f5f7fa;
}
.params-panel-body .el-tabs__item {
  font-size: 0.8rem; color: #546e7a;
}
.params-panel-body .el-tabs__item.is-active {
  color: #1976d2;
  font-weight: 600;
}
.params-panel-body .el-tabs__nav-wrap::after {
  background-color: #d9ecff;
}
.params-panel-body .el-tabs--top .el-tabs__item.is-top:last-child {
  padding-right: 16px;
}

/* Param section cards - light cards with subtle border */
.param-section-card {
  background: #ffffff;
  border: 1px solid #e0ecf7;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}
.param-section-title {
  font-weight: 600; font-size: 0.78rem; color: #1976d2;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e8f0fe;
  letter-spacing: 0.2px;
  text-transform: uppercase;
}

/* Property page key text (static, no border) */
.param-key-text {
  font-size: 0.8rem; font-weight: 600; color: #37474f;
  min-width: 140px; padding: 2px 4px;
  background: transparent; border: none;
}

/* Test items list - custom styling */
.params-panel-body .test-items-list {
  display: flex; flex-direction: column; gap: 6px;
  max-height: 280px; overflow-y: auto;
}
.params-panel-body .test-item-row {
  background: #ffffff;
  border: 1px solid #e0ecf7;
  border-radius: 6px;
  padding: 10px 12px;
  display: flex; align-items: center; gap: 10px;
  transition: all 0.15s ease;
}
.params-panel-body .test-item-row:hover {
  border-color: #b3d4fc;
  box-shadow: 0 1px 4px rgba(25,118,210,0.08);
  background: #fafbfc;
}
.params-panel-body .test-item-name {
  flex: 1; min-width: 0;
  font-size: 0.82rem; font-weight: 500; color: #263238;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.params-panel-body .test-item-name.critical {
  font-weight: 600; color: #c62828;
}
.params-panel-body .test-item-tags {
  display: flex; flex-wrap: wrap; gap: 4px;
  margin-left: auto;
}
.params-panel-body .test-item-tag {
  font-size: 0.65rem; height: 20px; line-height: 16px;
  padding: 0 6px; border-radius: 3px;
  font-weight: 500;
}
.params-panel-body .test-item-tag.type { background: #e3f2fd; color: #1565c0; }
.params-panel-body .test-item-tag.critical { background: #fdeaea; color: #c62828; }
.params-panel-body .test-item-tag.block { background: #fff8e1; color: #f57f17; }
.params-panel-body .test-item-service {
  font-size: 0.7rem; color: #78909c;
  max-width: 180px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-left: 8px; flex-shrink: 0;
}
.params-panel-body .test-item-checkbox { flex-shrink: 0; }

/* Override form controls for light panel theme */
.params-panel-body .el-form-item { margin-bottom: 12px; }
.params-panel-body .el-form-item__label { 
  font-size: 0.8rem; color: #455a64; font-weight: 500; 
  line-height: 1.4;
}
.params-panel-body .el-input__inner,
.params-panel-body .el-select .el-input__inner {
  background: #ffffff; border-color: #cfd8e0; color: #263238;
  font-size: 0.82rem; height: 32px;
  border-radius: 4px;
}
.params-panel-body .el-input__inner:focus {
  border-color: #1976d2;
  box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.12);
}
.params-panel-body .el-input.is-disabled .el-input__inner {
  background: #f0f2f5; color: #909399;
}
.params-panel-body .el-switch__label { color: #546e7a; font-size: 0.78rem; }
.params-panel-body .el-table { background: #ffffff; color: #333; font-size: 0.78rem; }
.params-panel-body .el-table th.el-table__cell { background: #eef4fb; color: #1565c0; font-size: 0.75rem; font-weight: 600; }
.params-panel-body .el-table tr { background: #ffffff; }
.params-panel-body .el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell { background: #f8faff; }
.params-panel-body .el-table td.el-table__cell { border-bottom-color: #e8eef5; }
.params-panel-body .el-checkbox__label { font-size: 0.78rem; color: #455a64; }
.params-panel-body .el-tag { font-size: 0.7rem; }
.params-panel-body .el-select .el-select__tags-text { font-size: 0.78rem; }
.params-panel-body .el-form-item--small.el-form-item { margin-bottom: 8px; }

/* Form grid improvements */
.params-panel-body .el-row { margin-bottom: 4px; }
.params-panel-body .el-col { padding: 0 6px; }

/* Tabs light theme overrides */
.params-tabs.el-tabs { background: transparent; }
.params-tabs.el-tabs--top > .el-tabs__header { background: #ffffff; margin-bottom: 12px; border-radius: 6px 6px 0 0; border-bottom: 1px solid #e0ecf7; padding: 0 4px; }
.params-tabs .el-tabs__item { height: 34px; line-height: 34px; font-size: 0.8rem; padding: 0 14px; font-weight: 500; }
.params-tabs .el-tabs__active-bar { background: #1976d2; height: 3px; }
</style>

<style>
.log-panel {
  flex-shrink: 0;
  position: relative;
  background: #0d1b2a;
  border-top: 2px solid #1976d2; display: flex; flex-direction: column;
  font-family: 'SF Mono','Consolas',monospace; font-size: 0.78rem;
}
.log-resize-handle {
  position: absolute; top: -4px; left: 0; right: 0; height: 8px;
  cursor: ns-resize; z-index: 1;
}
.log-resize-handle:hover { background: rgba(100,181,246,0.15); }
.log-panel-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 4px 14px; background: #0a1522;
  border-bottom: 1px solid #1e3350; color: #b0c4de; flex-shrink: 0;
}
.log-led { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #00e676; box-shadow: 0 0 4px #00e676; margin-right: 6px; }
.log-header-actions { display: flex; gap: 8px; }
.log-header-btn { font-size: 0.75rem; cursor: pointer; color: #546e7a; }
.log-header-btn:hover { color: #b0c4de; }
.log-panel-body-wrapper {
  display: flex; flex: 1; overflow: hidden;
}
.log-filter-sidebar {
  width: 44px; flex-shrink: 0;
  display: flex; flex-direction: column;
  border-right: 1px solid #1e3350;
  padding: 6px 0;
  background: #0a1522;
  align-items: stretch;
}
.log-filter-item {
  display: flex; align-items: center; justify-content: center;
  padding: 5px 2px; cursor: pointer;
  font-size: 0.7rem; font-weight: 700;
  transition: all 0.1s;
  border-left: 3px solid transparent;
  text-align: center;
}
.log-filter-item:hover { background: #1a2d47; }
.log-filter-item.active { background: rgba(255,255,255,0.05); }
.filter-label { line-height: 1.2; }
.log-panel-body { flex: 1; overflow-y: auto; padding: 2px 0; }
.log-line {
  padding: 1px 10px; display: flex; gap: 8px; align-items: baseline;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}
.log-time { color: #546e7a; flex-shrink: 0; min-width: 70px; }
.log-msg { color: #b0c4de; word-break: break-all; }
.log-info .log-msg { color: #b0c4de; }
.log-warn .log-msg { color: #ffc107; font-weight: 600; }
.log-error .log-msg { color: #ef5350; font-weight: 600; }
.log-empty { color: #546e7a; text-align: center; padding: 8px; }
</style>