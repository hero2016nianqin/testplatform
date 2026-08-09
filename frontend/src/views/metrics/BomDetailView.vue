<template>
  <div class="min-w-0" :class="{ 'compact-mode': compact }">
    <div v-if="loading" v-loading="loading" style="height:300px" />

    <template v-else>
      <!-- Top Bar: BOM Info + Actions -->
      <div class="bg-white border border-gray-200 rounded-lg shadow-sm px-4 py-2.5 mb-2 flex items-center justify-between flex-wrap gap-x-3 gap-y-1.5">
        <div class="flex items-center gap-2">
          <el-tag size="small" :type="bom.status === 1 ? 'success' : 'info'" class="ml-1">
            {{ bom.status === 1 ? '启用' : '停用' }}
          </el-tag>
          <el-divider direction="vertical" />
          <span class="text-xs text-gray-500 whitespace-nowrap">编码：{{ bom.bom_code }} ｜ 名称：{{ bom.bom_name }}</span>
          <span class="text-xs text-gray-500 whitespace-nowrap">集合：{{ collectionName }} v{{ bom.collection_version ?? '?' }} ｜ BOM v{{ bom.version }}-{{ versionStatusText(bom) }}</span>
        </div>
        <div class="flex items-center gap-1.5 flex-wrap">
          <!-- View Toggle -->
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button label="all">全部</el-radio-button>
            <el-radio-button label="empty">未填写</el-radio-button>
            <el-radio-button label="filled">已填写</el-radio-button>
            <el-radio-button label="diff">有差异</el-radio-button>
          </el-radio-group>
          <!-- UI Mode Toggle -->
          <el-radio-group v-model="uiMode" size="small">
            <el-radio-button label="browse">浏览紧凑</el-radio-button>
            <el-radio-button label="edit">编辑专注</el-radio-button>
          </el-radio-group>
          <!-- Compact Toggle -->
          <el-tooltip content="紧凑模式：缩小间距，一屏展示更多测试项" placement="bottom" :show-after="200">
            <span class="flex items-center cursor-pointer" @click="compact = !compact">
              <el-switch v-model="compact" size="small" />
              <span class="ml-1 text-xs text-gray-600">紧凑</span>
            </span>
          </el-tooltip>
          <el-select v-model="processFilter" placeholder="选择工序" size="small" clearable style="width:140px" @change="stationFilter = ''">
            <el-option v-for="p in processOptions" :key="p" :label="p" :value="p" />
          </el-select>
          <el-select v-model="stationFilter" placeholder="选择工位" size="small" clearable style="width:140px" :disabled="!processFilter">
            <el-option v-for="s in stationOptions" :key="s" :label="s" :value="s" />
          </el-select>

          <!-- Review Status -->
          <template v-if="bom.review_status === 'pending'">
            <el-tag type="warning">待评审</el-tag>
          </template>
          <template v-else-if="bom.review_status === 'approved'">
            <el-tag type="success">评审通过</el-tag>
          </template>
          <template v-else-if="bom.review_status === 'rejected'">
            <el-tag type="danger">已驳回</el-tag>
          </template>
          <template v-if="bom.archived">
            <el-tag type="info">已归档</el-tag>
          </template>

          <!-- 在线用户 -->
          <el-tooltip :content="onlineUsers.length > 0 ? '在线协同编辑：' + onlineUsers.map(u => u.user_name).join('、') : '暂无其他人在线'" placement="top" :show-after="300">
            <div class="flex items-center gap-1.5" v-if="onlineUsers.length > 0">
              <el-avatar :size="24" v-for="u in onlineUsers.slice(0, 3)" :key="u.user_id" :src="getAvatarUrl(u.user_name)" class="ring-2 ring-white -ml-1">
                <template #text>{{ u.user_name.charAt(0).toUpperCase() }}</template>
              </el-avatar>
              <span v-if="onlineUsers.length > 3" class="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">+{{ onlineUsers.length - 3 }}</span>
              <span class="text-xs text-gray-500">{{ onlineUsers.length }}人在线</span>
            </div>
          </el-tooltip>

          <el-button size="small" class="font-bold" @click="openVersionDiff">
            <el-icon><DataAnalysis /></el-icon>版本对比
          </el-button>
          <el-tooltip content="高危操作：将所有参数值恢复为归档基准原值，覆盖当前编辑中的值。" placement="top" :show-after="300">
            <el-button size="small" class="font-bold" :disabled="bom.archived || bom.review_status === 'pending'" @click="handleResetDraft">
              <el-icon><Refresh /></el-icon>重置编辑
              <el-tag v-if="!bom.archived && bom.review_status !== 'pending'" size="small" type="danger" class="ml-1">高危</el-tag>
            </el-button>
          </el-tooltip>

          <!-- Pre-save Validation Button -->
          <el-button size="small" class="font-bold" v-if="!bom.archived && bom.review_status !== 'pending'" @click="validateAndSave">
            <el-icon><Check /></el-icon>参数校验
          </el-button>

          <!-- Review / Archive Buttons -->
          <el-button size="small" class="font-bold" v-if="bom.review_status === 'none' && !bom.archived" type="warning" @click="handleSubmitReview">
            提交评审
          </el-button>

          <!-- Export Dropdown -->
          <el-dropdown trigger="click" @command="handleExportAction">
            <el-button type="primary" size="small" class="font-bold">
              <el-icon><Download /></el-icon>导出<el-icon><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="config">配置文件 (JSON/INI)</el-dropdown-item>
                <el-dropdown-item command="excel">填写记录表 (Excel)</el-dropdown-item>
                <el-dropdown-item command="diff-report">差异对比报告 (Excel)</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <el-button size="small" class="font-bold" v-if="bom.review_status === 'pending'" type="info" @click="handleWithdrawReview">
            撤回评审
          </el-button>
          <el-button size="small" class="font-bold" v-if="bom.review_status === 'pending'" type="success" @click="handleApproveReview">
            评审通过
          </el-button>
          <el-button size="small" class="font-bold" v-if="bom.review_status === 'pending'" type="danger" @click="handleRejectReview">
            驳回
          </el-button>
          <el-button size="small" class="font-bold" v-if="bom.review_status === 'approved' && !bom.archived" type="primary" @click="handleArchive">
            归档
          </el-button>
           <el-button size="small" class="font-bold" v-if="bom.archived || bom.review_status === 'approved'" @click="handleNewIteration">
             基于此版本新建
           </el-button>
        </div>
      </div>

      <!-- Three-column Layout: Left Nav | Middle Content | Right Toolbar -->
      <div class="flex gap-4 mb-4">
        <!-- Left: Process→Station→Items Tree Navigation -->
        <div class="w-60 flex-shrink-0" v-if="showLeftNav && processTreeData.length">
          <el-card ref="navCardRef" shadow="never" class="max-h-[calc(100vh-200px)] overflow-y-auto sticky top-4">
            <!-- Search -->
            <div class="p-2 border-b">
              <el-input v-model="processSearch" size="small" placeholder="搜索工序/工位/测试项" clearable @input="onTreeSearch">
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
            </div>
            <!-- Tree -->
            <div class="px-1">
              <el-collapse v-model="expandedProcesses" accordion class="w-full">
                <el-collapse-item v-for="proc in filteredProcessTree" :key="proc.name" :name="proc.name">
                  <template #title>
                    <div class="flex items-center justify-between w-full px-1 py-0.5">
                      <div class="flex items-center gap-1.5 min-w-0">
                        <span class="text-gray-500 text-xs"><el-icon><OfficeBuilding /></el-icon></span>
                        <span class="font-medium text-sm truncate">{{ proc.name }}</span>
                      </div>
                      <div class="flex items-center gap-1 flex-shrink-0">
                        <span v-if="proc.diffCount > 0" class="text-amber-600 text-[10px] font-bold bg-amber-50 px-1.5 py-0.5 rounded">{{ proc.diffCount }} 异</span>
                        <span v-if="proc.emptyParams > 0" class="text-red-600 text-[10px] font-bold bg-red-50 px-1.5 py-0.5 rounded">{{ proc.emptyParams }} 空</span>
                        <el-icon v-else class="text-green-600 text-xs"><Check /></el-icon>
                      </div>
                    </div>
                  </template>
                  <div class="px-1.5 py-1 space-y-1">
                    <div v-for="sta in proc.stations" :key="sta.name" class="border-l-2 border-gray-200 pl-1.5">
                      <!-- Station header: click to fold -->
                      <div class="flex items-center justify-between rounded px-1 py-1 cursor-pointer hover:bg-gray-100" @click="toggleNavStation(proc.name, sta.name)">
                        <div class="flex items-center gap-1 min-w-0">
                          <el-icon class="text-gray-400 flex-shrink-0" style="font-size:12px">
                            <ArrowRight v-if="!isNavStationExpanded(proc.name, sta.name)" /><ArrowDown v-else />
                          </el-icon>
                          <span class="text-xs font-medium text-gray-600 truncate">{{ sta.name }}</span>
                        </div>
                        <div class="flex items-center gap-1 flex-shrink-0">
                          <span v-if="sta.diffCount > 0" class="text-amber-500 text-[10px]">{{ sta.diffCount }} 异</span>
                          <span v-if="sta.emptyParams > 0" class="text-red-500 text-[10px]">{{ sta.emptyParams }} 空</span>
                          <el-icon v-else-if="sta.totalParams > 0" class="text-green-500 text-[10px]"><Check /></el-icon>
                        </div>
                      </div>
                      <!-- Station items (folding) -->
                      <div v-show="isNavStationExpanded(proc.name, sta.name)" class="space-y-0.5 mt-0.5">
                        <button v-for="itemInTree in sta.items" :key="itemInTree.id"
                          :data-nav-item="itemInTree.id"
                          class="w-full text-left text-xs px-2 py-1 rounded transition-colors flex items-center gap-1.5"
                          :class="navItemClass(itemInTree)"
                          @click="selectItem(itemInTree, proc.name, sta.name)">
                          <el-tooltip :content="getItemParamPreview(itemInTree)" placement="right" :show-after="300">
                            <span class="truncate flex-1">{{ itemInTree.name }}</span>
                          </el-tooltip>
                          <span v-if="itemDiffCount(itemInTree) > 0" class="text-amber-500 text-[10px] flex-shrink-0 font-bold">异{{ itemDiffCount(itemInTree) }}</span>
                          <span v-if="itemEmptyCount(itemInTree) > 0" class="text-red-500 text-[10px] flex-shrink-0 font-bold">空{{ itemEmptyCount(itemInTree) }}</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-card>
        </div>

        <!-- Middle: Process→Station Folding Cards -->
        <div class="flex-1 min-w-0">
          <div v-if="!processTreeData.length" class="text-center text-gray-400 py-12">
            <el-empty :description="emptyDescription" :image-size="60" />
          </div>

          <div v-else>
            <!-- Middle Toolbar: Expand/Collapse + Column Options -->
            <div class="flex items-center gap-2 mb-2 flex-wrap">
              <el-button size="small" @click="expandAllContent"><el-icon><ArrowDown /></el-icon>全部展开</el-button>
              <el-button size="small" @click="collapseAllContent"><el-icon><ArrowRight /></el-icon>全部折叠</el-button>
              <el-button size="small" type="warning" plain @click="expandOnlyDiff"><el-icon><DataAnalysis /></el-icon>仅展开差异</el-button>
              <el-divider direction="vertical" />
               <el-checkbox v-model="showBaselineCol" size="small">归档基准原值</el-checkbox>
               <el-divider direction="vertical" />
               <el-select v-model="domainFilter" size="small" style="width:140px" placeholder="领域筛选" clearable>
                 <el-option v-for="d in domainOptions" :key="d" :label="d" :value="d" />
               </el-select>
               <el-tag v-if="domainFilter !== '全部领域'" size="small" type="warning" class="ml-1">已筛选</el-tag>
              <span class="text-xs text-gray-400 ml-auto">Ctrl+S 保存全部 · ↑/↓ 切换测试项 · 编辑中 Tab 切换参数</span>
            </div>

            <div class="space-y-3">
            <!-- Process Card -->
            <div v-for="proc in processTreeData" :key="proc.name" :data-process="proc.name" class="border rounded-lg overflow-hidden" :class="{ 'border-red-300': proc.emptyParams > 0, 'border-green-300': proc.emptyParams === 0 && proc.totalParams > 0 }">
              <div class="bg-gray-50 px-4 py-2 border-b flex items-center justify-between" style="cursor:pointer" @click="toggleProcessExpand(proc.name)">
                <div class="flex items-center gap-2">
                  <el-icon :class="{ 'rotate-90': isProcessExpanded(proc.name) }" class="transition-transform"><ArrowRight /></el-icon>
                  <span class="font-medium text-sm">{{ proc.name }}</span>
                  <el-tag size="small" :type="proc.emptyParams > 0 ? 'danger' : 'success'">{{ proc.emptyParams > 0 ? `${proc.emptyParams} 个空参数` : '全部已填' }}</el-tag>
                  <el-tag v-if="proc.diffCount > 0" size="small" type="warning">{{ proc.diffCount }} 差异</el-tag>
                  <span class="text-xs text-gray-500">{{ proc.stations.length }} 个工位 · {{ proc.totalParams }} 个参数</span>
                </div>
                <div class="flex items-center gap-1" @click.stop>
                  <el-button size="small" @click="batchFillProcess(proc.name)" :disabled="bom.archived || bom.review_status === 'pending'"><el-icon><Edit /></el-icon>批量填充</el-button>
                  <el-button size="small" @click="copyPrevProcess(proc.name)" :disabled="bom.archived || bom.review_status === 'pending'"><el-icon><CopyDocument /></el-icon>复制上工序</el-button>
                  <el-button size="small" @click="clearProcessParams(proc.name)" :disabled="bom.archived || bom.review_status === 'pending'"><el-icon><Delete /></el-icon>清空</el-button>
                </div>
              </div>

              <!-- Station Cards (show when process expanded) -->
              <div v-show="isProcessExpanded(proc.name)">
                <div v-for="sta in proc.stations" :key="sta.name" :data-station="sta.name" class="border-t">
                  <!-- Station Header -->
                  <div class="px-4 py-1.5 flex items-center justify-between bg-white" style="cursor:pointer" @click="toggleStationExpand(proc.name, sta.name)">
                    <div class="flex items-center gap-2">
                      <el-icon v-if="isStationExpanded(proc.name, sta.name)"><ArrowDown /></el-icon>
                      <el-icon v-else><ArrowRight /></el-icon>
                      <span class="text-sm font-medium">{{ sta.name }}</span>
                      <el-tag size="small" :type="sta.emptyParams > 0 ? 'danger' : 'success'">{{ sta.emptyParams > 0 ? `${sta.emptyParams} 空` : '已填' }}</el-tag>
                      <el-tag v-if="sta.diffCount > 0" size="small" type="warning">{{ sta.diffCount }} 差异</el-tag>
                      <span class="text-xs text-gray-400">{{ sta.items.length }} 项 · {{ sta.totalParams }} 参数</span>
                    </div>
                    <div class="flex items-center gap-1" @click.stop>
                      <el-button size="small" @click="batchFillStation(proc.name, sta.name)" :disabled="bom.archived || bom.review_status === 'pending'"><el-icon><Edit /></el-icon>批量填充</el-button>
                      <el-button size="small" @click="exportStationExcel(proc.name, sta.name)" :disabled="bom.archived || bom.review_status === 'pending'"><el-icon><Download /></el-icon>导出</el-button>
                      <el-button size="small" @click="syncStationFromHistory(proc.name, sta.name)" :disabled="bom.archived || bom.review_status === 'pending'"><el-icon><Refresh /></el-icon>同步历史</el-button>
                      <el-button size="small" @click="clearStationParams(proc.name, sta.name)" :disabled="bom.archived || bom.review_status === 'pending'"><el-icon><Delete /></el-icon>清空</el-button>
                      <el-button size="small" type="primary" @click="copyPrevStation(proc.name, sta.name)" :disabled="bom.archived || bom.review_status === 'pending'"><el-icon><CopyDocument /></el-icon>复制上工位</el-button>
                    </div>
                  </div>

                  <!-- Station Content: per-item tables -->
                  <div v-show="isStationExpanded(proc.name, sta.name)" class="px-4 py-2 space-y-2 bg-gray-50">
                    <div v-for="item in sta.items" :key="item.id" :id="`item-${item.id}`" class="border rounded cursor-pointer transition-shadow" :class="[itemHasParams(item) ? 'p-2' : 'p-0.5', itemBgClass(item), { 'border-red-200': hasEmptyParams(item), 'border-blue-400 ring-2 ring-blue-200': isSelectedItem(item) || navItemId === item.id }]" @click.stop="selectItem(item, proc.name, sta.name)">
                      <div class="flex items-center justify-between" :class="itemHasParams(item) ? 'mb-1.5' : 'mb-0'">
                        <div class="flex items-center gap-2 min-w-0">
                          <el-tooltip v-if="!canEditItem(item)" :content="itemReadonlyReason(item)" placement="top" :show-after="200">
                            <span class="flex items-center text-gray-400 flex-shrink-0"><el-icon><Lock /></el-icon></span>
                          </el-tooltip>
                          <span class="text-sm font-medium truncate">{{ item.name }}</span>
                          <el-tag v-if="itemHasParams(item)" size="small" :type="item.block_type === 'must_test' ? 'danger' : item.block_type === 'critical' ? 'warning' : 'info'" class="text-xs">{{ item.block_type === 'must_test' ? '必测' : item.block_type === 'critical' ? '关键' : '普通' }}</el-tag>
                          <el-tag v-if="hasEmptyParams(item)" size="small" type="danger">{{ emptyParamCount(item) }} 空</el-tag>
                           <el-tag v-if="item.domain" size="small" type="primary" class="text-xs" effect="plain">{{ item.domain }}</el-tag>
                           <el-tag v-if="itemOwnerName(item)" size="small" type="success" class="text-xs" effect="plain">负责人：{{ itemOwnerName(item) }}</el-tag>
                          <el-tag v-if="!canEditItem(item)" size="small" type="info" class="text-xs" effect="plain">只读</el-tag>
                        </div>
                        <div class="flex items-center gap-1 flex-shrink-0">
                          <el-tooltip content="查看该测试项的参数变更记录" placement="top" :show-after="200">
                            <el-button size="small" text @click.stop="openChangeLogDialog(item)"><el-icon><Clock /></el-icon></el-button>
                          </el-tooltip>
                        </div>
                      </div>
                      <div v-if="itemHasParams(item)">
                        <el-table :data="getItemParamRows(item)" stripe size="small" style="width:100%" :row-class-name="paramRowClass" @row-click="(r: any) => startInlineEdit(r)">
                          <el-table-column label="参数" width="120">
                            <template #default="{ row }">
                              <div class="flex items-center gap-1">
                                <el-tooltip :content="`数据格式：${paramFormatLabel(row.format)}`" placement="top">
                                  <span class="text-xs">{{ row.label }}</span>
                                </el-tooltip>
                                <el-tag v-if="row.required" size="small" type="danger" class="text-xs">必填</el-tag>
                              </div>
                            </template>
                          </el-table-column>
                          <el-table-column label="参数值" min-width="160">
                            <template #default="{ row }">
                              <div :class="['param-cell', { 'param-dirty': isParamDirty(row.indicator_id, row.param_key), 'param-empty': isParamEmpty(row._ind, row.param_key) }]">
                                <div v-if="!bom.archived && bom.review_status !== 'pending' && canEditItem(item) && editParamKey === row._bom_indicator_id + '#val#' + row.param_key && !isListFormat(row.format)" class="flex items-center gap-1" @click.stop>
                                  <el-select v-if="row.format === 'boolean'" v-model="row._ind._param_map[row.param_key].value" size="small" style="width:110px" @change="saveDraft(); saveParamValue(row._ind, row.param_key)">
                                    <el-option label="true" value="true" />
                                    <el-option label="false" value="false" />
                                  </el-select>
                                  <el-input v-else-if="['number', 'range', 'percent'].includes(row.format)" v-model="row._ind._param_map[row.param_key].value" size="small" style="width:110px" @update:model-value="saveDraft()" @blur="validateAndSaveParam(row._ind, row.param_key)" @keyup.enter="validateAndSaveParam(row._ind, row.param_key)" @keydown.tab="onInlineEditKeydown($event, row, item)" />
                                  <el-input v-else v-model="row._ind._param_map[row.param_key].value" size="small" style="width:110px" @update:model-value="saveDraft()" @blur="saveParamValue(row._ind, row.param_key)" @keyup.enter="saveParamValue(row._ind, row.param_key)" @keydown.tab="onInlineEditKeydown($event, row, item)" />
                                </div>
                                <div v-else-if="isListFormat(row.format)" class="flex items-center gap-1 cursor-pointer" style="min-height:24px" :class="{ 'cursor-not-allowed opacity-60': !canEditItem(item) }" @click.stop="canEditItem(item) && openListEditor(row)" :title="listDisplay(row)">
                                  <span class="text-xs truncate max-w-[180px]" :class="{ 'text-danger font-medium': isParamDirty(row.indicator_id, row.param_key), 'text-red-600': isParamEmpty(row._ind, row.param_key) }">{{ listDisplay(row) }}</span>
                                  <el-tag size="small" type="info" class="flex-shrink-0">列表</el-tag>
                                </div>
                                <el-tooltip v-if="!canEditItem(item) && !isListFormat(row.format)" :content="itemReadonlyReason(item) || '该测试项无编辑权限'" placement="top" :show-after="200">
                                  <span class="text-xs" :class="{ 'text-danger font-medium': isParamDirty(row.indicator_id, row.param_key), 'text-red-600': isParamEmpty(row._ind, row.param_key), 'cursor-not-allowed opacity-60': !canEditItem(item) }" style="cursor:pointer" @click="canEditItem(item) && startInlineEdit(row)">
                                    {{ row._ind._param_map?.[row.param_key]?.value || '-' }}
                                  </span>
                                </el-tooltip>
                                <span v-else-if="!isListFormat(row.format)" class="text-xs" :class="{ 'text-danger font-medium': isParamDirty(row.indicator_id, row.param_key), 'text-red-600': isParamEmpty(row._ind, row.param_key), 'cursor-not-allowed opacity-60': !canEditItem(item) }" style="cursor:pointer" @click="canEditItem(item) && startInlineEdit(row)">
                                  {{ row._ind._param_map?.[row.param_key]?.value || '-' }}
                                </span>
                              </div>
                            </template>
                          </el-table-column>
                          <el-table-column v-if="showBaselineCol" label="归档原值" width="150">
                            <template #default="{ row }">
                              <div class="flex items-center gap-1">
                                <span class="text-xs">{{ baselineParams[row.indicator_id + '#' + row.param_key] ?? '-' }}</span>
                                <el-tooltip content="复制归档基准原值到当前值" placement="top" :show-after="300">
                                  <el-button v-if="baselineParams[row.indicator_id + '#' + row.param_key] !== undefined" class="copy-baseline-btn" size="small" text type="primary" :disabled="bom.archived || bom.review_status === 'pending' || !canEditItem(item)" @click.stop="copyBaselineValue(row)">
                                    <el-icon><CopyDocument /></el-icon>
                                  </el-button>
                                </el-tooltip>
                              </div>
                            </template>
                          </el-table-column>
                          <el-table-column label="领域" width="110">
                            <template #default>
                              <span class="text-xs" :class="{ 'text-gray-400': !item.domain }">{{ item.domain || '-' }}</span>
                            </template>
                          </el-table-column>
                           <el-table-column label="负责人" width="160">
                             <template #default>
                               <div class="flex items-center gap-1" @click.stop>
                                 <el-tooltip :content="itemOwnerName(item) ? '责任人：' + itemOwnerName(item) + '。如需修改，请前往领域责任人维护界面' : '未指定负责人。如需分配，请前往领域责任人维护界面'" placement="top" :show-after="200">
                                   <span class="text-xs" :class="itemOwnerName(item) ? '' : 'text-gray-400'">{{ itemOwnerName(item) || '未指定' }}</span>
                                 </el-tooltip>
                               </div>
                             </template>
                           </el-table-column>
                          <el-table-column label="备注" width="60">
                            <template #default="{ row }">
                              <el-tooltip v-if="row.remark" :content="row.remark" placement="top">
                                <el-icon style="color:#999;cursor:help;font-size:14px"><InfoFilled /></el-icon>
                              </el-tooltip>
                            </template>
                          </el-table-column>
                        </el-table>
                      </div>
                      <div v-else class="text-xs text-gray-400 py-1">该测试项暂未绑定指标</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          </div>
        </div>

        <!-- Right: Multi-tab Tool Panel -->
        <BomDetailToolPanel
          :bom="bom"
          :expanded="uiMode === 'edit'"
          :fill-percent="fillProgress().percent"
          :bom-stats="bomStats"
          @batch-fill="(u, l) => { rightToolbar.batchFillThreshold.upper = u || ''; rightToolbar.batchFillThreshold.lower = l || ''; batchFillThreshold() }"
          @copy-selected="copySelectedItems"
          @paste-to-selected="pasteToSelected"
          @clear-selected="clearSelectedParams"
          @filter-empty="filterEmptyParams"
          @export-template="exportExcelTemplate"
          @export-config="(dim: string) => { rightToolbar.exportDimension = dim; exportCurrentConfig() }"
          @export-diff-report="exportDiffReport"
          @export-pdf="exportPdfReport"
          @import-excel="openImport"
          @toggle-panel="rightToolbar.visible = !rightToolbar.visible"
        />
      </div>
    <!-- Export Dialog -->
    <el-dialog v-model="exportDialog.visible" title="导出配置文件" width="420px">
      <el-form>
        <el-form-item label="输出格式">
          <el-select v-model="exportDialog.format" class="w-full">
            <el-option label="JSON" value="json" />
            <el-option label="INI" value="ini" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exportDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="exporting" @click="submitExport">确认导出</el-button>
      </template>
    </el-dialog>

    <!-- List Param Edit Dialog -->
    <el-dialog v-model="listEditDialog.visible" title="编辑列表参数" width="460px" :close-on-click-modal="false">
      <div class="flex items-center gap-2 mb-3">
        <span class="text-sm font-medium">{{ listEditDialog.label }}</span>
        <el-tag size="small" type="info">{{ paramFormatLabel(listEditDialog.format) }}</el-tag>
      </div>
      <el-input v-model="listEditDialog.value" type="textarea" :rows="7" placeholder="多个值用英文逗号分隔，例如：1,2,3&#10;或每行一个值" />
      <div class="text-xs text-gray-400 mt-2">保存时将自动规范化：中文逗号转为英文逗号，并去除空值</div>
      <template #footer>
        <el-button @click="listEditDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="listEditDialog.saving" @click="saveListEditor">确定</el-button>
      </template>
    </el-dialog>

    <!-- Version Diff Dialog -->
    <el-dialog v-model="diffDialog.visible" title="版本差异对比" width="1000px" top="5vh" :close-on-click-modal="false">
      <div v-if="diffDialog.loading" v-loading="diffDialog.loading" style="height:200px" />
      <template v-else>
        <div class="flex items-start gap-4 mb-4 flex-wrap">
          <div class="flex flex-col gap-2">
            <div class="flex items-center gap-2">
              <span class="text-sm text-gray-600 font-medium">BOM编码：</span>
              <el-autocomplete
                v-model="diffDialog.bomCode"
                :fetch-suggestions="queryBomSuggestions"
                placeholder="输入BOM编码检索归档版本"
                size="small"
                style="width:260px"
                clearable
                @select="onDiffBomSelected"
              >
                <template #default="{ item }">
                  <div class="flex items-center justify-between w-full">
                    <span class="font-medium">{{ item.bom_code }}</span>
                    <span class="text-xs text-gray-500 ml-3">{{ item.versions }}</span>
                  </div>
                </template>
              </el-autocomplete>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-sm text-gray-600 font-medium">已发布版本号：</span>
              <el-select
                v-model="diffDialog.selectedSnapshotId"
                placeholder="选择已发布版本号"
                size="small"
                style="width:200px"
                :disabled="!diffDialog.publishedVersions.length"
                @change="onVersionChange"
              >
                <el-option v-for="v in versionOptions" :key="v.id" :value="v.id" :label="versionOptionLabel(v)" />
              </el-select>
            </div>
          </div>
          <el-button type="primary" size="small" :loading="diffDialog.loading" :disabled="!diffDialog.selectedSnapshotId" @click="loadArchivedDiff">对比</el-button>
        </div>

        <el-empty v-if="!diffDialog.added.newItems.length && !diffDialog.added.newParams.length && !diffDialog.removed.deletedItems.length && !diffDialog.removed.deletedParams.length && !diffDialog.modified.length" description="当前版本与所选已发布版本测试项、参数配置完全一致，无差异" :image-size="50" />

        <!-- Added: New test items + new params -->
        <div v-if="diffDialog.added.newItems.length || diffDialog.added.newParams.length" class="mb-6">
          <h4 class="font-bold text-sm mb-2" style="color:#67c23a">
            <el-icon><CirclePlus /></el-icon>
            新增内容（{{ diffDialog.added.newItems.length + diffDialog.added.newParams.length }}）
          </h4>
          <div v-if="diffDialog.added.newItems.length" class="mb-3">
            <div class="text-xs text-gray-400 mb-1">新增测试项</div>
            <el-table :data="diffDialog.added.newItems" stripe size="small" style="width:100%" row-class-name="diff-added-row">
              <el-table-column prop="code" label="编码" width="120" />
              <el-table-column prop="name" label="名称" width="140" />
              <el-table-column label="工序" width="100"><template #default="{ row }">{{ row.process_name || '-' }}</template></el-table-column>
              <el-table-column label="工位" width="100"><template #default="{ row }">{{ row.station_name || '-' }}</template></el-table-column>
            </el-table>
          </div>
          <div v-if="diffDialog.added.newParams.length">
            <div class="text-xs text-gray-400 mb-1">新增参数（同测试项下）</div>
            <el-table :data="diffDialog.added.newParams" stripe size="small" style="width:100%" row-class-name="diff-added-row" :span-method="diffSpanMethodAdded">
              <el-table-column prop="indicatorName" label="测试项" width="130" />
              <el-table-column label="工序" width="80"><template #default="{ row }">{{ row.process_name || '-' }}</template></el-table-column>
              <el-table-column label="工位" width="80"><template #default="{ row }">{{ row.station_name || '-' }}</template></el-table-column>
              <el-table-column prop="paramName" label="参数名称" width="130" />
              <el-table-column label="新值" min-width="200"><template #default="{ row }">{{ row.newValue ?? '-' }}</template></el-table-column>
            </el-table>
          </div>
        </div>

        <!-- Removed: Deleted test items + removed params -->
        <div v-if="diffDialog.removed.deletedItems.length || diffDialog.removed.deletedParams.length" class="mb-6">
          <h4 class="font-bold text-sm mb-2" style="color:#f56c6c">
            <el-icon><Remove /></el-icon>
            删除内容（{{ diffDialog.removed.deletedItems.length + diffDialog.removed.deletedParams.length }}）
          </h4>
          <div v-if="diffDialog.removed.deletedItems.length" class="mb-3">
            <div class="text-xs text-gray-400 mb-1">删除测试项</div>
            <el-table :data="diffDialog.removed.deletedItems" stripe size="small" style="width:100%" row-class-name="diff-removed-row">
              <el-table-column prop="code" label="编码" width="120" />
              <el-table-column prop="name" label="名称" width="140" />
              <el-table-column label="工序" width="100"><template #default="{ row }">{{ row.process_name || '-' }}</template></el-table-column>
              <el-table-column label="工位" width="100"><template #default="{ row }">{{ row.station_name || '-' }}</template></el-table-column>
            </el-table>
          </div>
          <div v-if="diffDialog.removed.deletedParams.length">
            <div class="text-xs text-gray-400 mb-1">删除参数（同测试项下）</div>
            <el-table :data="diffDialog.removed.deletedParams" stripe size="small" style="width:100%" row-class-name="diff-removed-row" :span-method="diffSpanMethodRemoved">
              <el-table-column prop="indicatorName" label="测试项" width="130" />
              <el-table-column label="工序" width="80"><template #default="{ row }">{{ row.process_name || '-' }}</template></el-table-column>
              <el-table-column label="工位" width="80"><template #default="{ row }">{{ row.station_name || '-' }}</template></el-table-column>
              <el-table-column prop="paramName" label="参数名称" width="130" />
              <el-table-column label="归档原值" min-width="200"><template #default="{ row }">{{ row.oldValue ?? '-' }}</template></el-table-column>
            </el-table>
          </div>
        </div>

        <!-- Modified: Params changed -->
        <div v-if="diffDialog.modified.length" class="mb-6">
          <h4 class="font-bold text-sm mb-2" style="color:#e6a23c">
            <el-icon><WarningFilled /></el-icon>
            参数修改（{{ diffDialog.modified.length }}）
          </h4>
          <el-table :data="diffDialog.modified" stripe size="small" style="width:100%" :span-method="diffSpanMethod">
            <el-table-column prop="indicatorName" label="测试项" width="130" />
            <el-table-column label="工序" width="80"><template #default="{ row }">{{ row.process_name || '-' }}</template></el-table-column>
            <el-table-column label="工位" width="80"><template #default="{ row }">{{ row.station_name || '-' }}</template></el-table-column>
            <el-table-column label="参数" min-width="130">
              <template #default="{ row }">{{ row.paramName }}</template>
            </el-table-column>
            <el-table-column label="归档原值" min-width="160">
              <template #default="{ row }">
                <span class="text-gray-400 line-through">{{ row.oldValue ?? '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="当前新值" min-width="160">
              <template #default="{ row }">
                <span class="text-danger font-medium">{{ row.newValue ?? '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="差异字段" width="120">
              <template #default="{ row }">{{ row.diffLabel || '-' }}</template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </el-dialog>

    <!-- Validation Dialog -->
    <el-dialog v-model="validationDialog.visible" title="参数校验" width="600px" top="10vh" :close-on-click-modal="false" :close-on-press-escape="true" @open="onValidationOpen">
      <div v-loading.lock="validationDialog.loading" element-loading-text="正在校验..." style="min-height:120px">
        <template v-if="!validationDialog.loading">
          <div v-if="validationErrors.length" class="mb-4">
            <el-alert title="校验未通过" type="error" :description="`发现 ${validationErrors.length} 个参数为空`" show-icon />
          </div>
          <div v-else class="mb-4">
            <el-alert title="校验通过" type="success" description="所有参数已填写完毕" show-icon />
          </div>

          <el-table v-if="validationErrors.length" :data="validationErrors" stripe size="small" style="width:100%" max-height="400">
            <el-table-column label="指标" min-width="140">
              <template #default="{ row }">{{ row.indicator_name || row.indicator_code || '-' }}</template>
            </el-table-column>
            <el-table-column label="参数" min-width="120">
              <template #default="{ row }">{{ row.param_name || row.param_key || '-' }}</template>
            </el-table-column>
            <el-table-column label="错误信息" min-width="180">
              <template #default="{ row }">{{ row.message }}</template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button size="small" type="primary" link @click="scrollToError(row)">定位</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="validationError" class="mt-3">
            <el-alert title="校验异常" type="error" :description="validationError" show-icon />
          </div>
        </template>
      </div>
      <template #footer>
        <el-button :loading="validationDialog.loading" @click="validationDialog.visible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 协同编辑冲突提示 -->
    <el-dialog v-model="conflictDialog.visible" title="保存冲突提示" width="600px" top="15vh" :close-on-click-modal="false">
      <el-alert title="部分参数保存失败" type="warning" :description="`以下 ${conflictDialog.conflicts.length} 项因版本冲突或权限不足未能保存，页面已刷新为最新数据，请重新编辑。`" show-icon class="mb-4" />
      <el-table :data="conflictDialog.conflicts" stripe size="small" style="width:100%" max-height="320">
        <el-table-column label="指标" min-width="90">
          <template #default="{ row }">#{{ row.indicator_id }}</template>
        </el-table-column>
        <el-table-column prop="message" label="冲突原因" min-width="260" />
        <el-table-column label="当前版本" width="100">
          <template #default="{ row }">{{ row.current_revision ?? '-' }}</template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button type="primary" @click="conflictDialog.visible = false">知道了</el-button>
      </template>
    </el-dialog>

    <!-- 参数变更记录 -->
    <el-dialog v-model="changeLogDialog.visible" :title="`变更记录${changeLogDialog.itemName ? '：' + changeLogDialog.itemName : ''}`" width="760px" top="10vh" :close-on-click-modal="false">
      <div v-loading="changeLogDialog.loading" style="min-height:120px">
        <el-empty v-if="!changeLogDialog.loading && !changeLogDialog.logs.length" description="暂无变更记录" />
        <el-table v-else :data="changeLogDialog.logs" stripe size="small" style="width:100%" max-height="420">
          <el-table-column label="时间" width="150">
            <template #default="{ row }">{{ row.created_at?.replace('T', ' ').slice(0, 19) || '-' }}</template>
          </el-table-column>
          <el-table-column prop="indicator_name" label="指标" min-width="140">
            <template #default="{ row }">{{ row.indicator_name || row.indicator_code || `#${row.indicator_id}` }}</template>
          </el-table-column>
          <el-table-column prop="param_name" label="参数" width="110">
            <template #default="{ row }">{{ row.param_name || row.param_key || '-' }}</template>
          </el-table-column>
          <el-table-column label="原值" min-width="110">
            <template #default="{ row }"><span class="text-gray-500">{{ row.old_value ?? '-' }}</span></template>
          </el-table-column>
          <el-table-column label="新值" min-width="110">
            <template #default="{ row }"><span class="font-medium" :class="{ 'text-danger': row.old_value !== row.new_value }">{{ row.new_value ?? '-' }}</span></template>
          </el-table-column>
          <el-table-column prop="operator_name" label="操作人" width="100" />
        </el-table>
      </div>
      <template #footer>
        <el-button @click="changeLogDialog.visible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- Excel Import Dialog -->
    <el-dialog v-model="importDialog.visible" title="Excel 导入" width="500px" top="10vh">
      <div v-loading="importDialog.loading">
        <p class="text-sm text-gray-600 mb-4">
          选择 Excel 文件导入后，将按「工序 + 工位 + 测试项 + 参数 Key」精确匹配并回填参数值。
        </p>
        <el-alert title="导入将覆盖现有参数值，建议先导出当前配置备份" type="warning" :closable="false" show-icon class="mb-4" />
        <div v-if="importResult" class="import-result">
          <el-alert :title="`导入完成：${importResult.updated || 0} 条更新，${importResult.errors || 0} 条错误`" :type="importResult.errors ? 'warning' : 'success'" show-icon />
          <div v-if="importResult.errors_list?.length" class="mt-2">
            <div v-for="(err, i) in importResult.errors_list" :key="i" class="text-xs text-red-500">{{ err }}</div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button v-if="!importResult" :loading="importDialog.loading" @click="importExcel">选择文件并导入</el-button>
        <el-button @click="importDialog.visible = false; importResult = null">关闭</el-button>
      </template>
    </el-dialog>
  </template>
  </div>
</template>

<script setup lang="ts">
import { Plus, Refresh, InfoFilled, DataAnalysis, ArrowRight, ArrowDown, CopyDocument, DocumentAdd, Delete, Search, Check, ArrowUp, Download, Upload, Filter, Edit, OfficeBuilding, Lock, Clock } from '@element-plus/icons-vue'
import { ref, reactive, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter, onBeforeRouteUpdate } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { metricsApi } from '@/api/metrics'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import BomDetailToolPanel from './BomDetailToolPanel.vue'

const STORAGE_KEY = 'bom_draft_'
const DOMAIN_FILTER_KEY = 'bom_domain_filter_'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const currentUser = authStore.user
const isSuperAdmin = computed(() => currentUser.value?.role === 'super_admin')
const isBomCreator = computed(() => {
  const me = currentUser.value?.username || currentUser.value?.display_name || ''
  return bom.created_by === me || bom.created_by === currentUser.value?.username
})
const configId = ref(Number(route.params.id))

const loading = ref(true)
const bom = reactive<any>({ bom_code: '', bom_name: '', status: 1, version: 1, collection_id: 0 })
const collectionName = ref('')
const testItems = ref<any[]>([])
// 测试项级保存串行队列：同一测试项的多次内联保存按序执行，
// 保证 item_revision 每次保存后都同步，避免快速连续编辑触发误报冲突。
const itemSaveQueues: Record<number, Promise<any>> = {}

function enqueueItemSave(itemId: number, task: () => Promise<any>): Promise<any> {
  const prev = itemSaveQueues[itemId] || Promise.resolve()
  const next = prev.then(task, task)
  itemSaveQueues[itemId] = next
  return next
}
const bomIndicators = ref<any[]>([])
const navCardRef = ref<any>(null)
const navItemId = ref<number | null>(null)

// ── View Mode & Progress ──
const viewMode = ref<'all' | 'empty' | 'filled' | 'diff'>('all')
const processSearch = ref('')
const stationFilter = ref('')
const domainFilter = ref('全部领域')
const domainOptions = ref<string[]>(['全部领域'])
const expandedProcesses = ref<string[]>([])

function saveDomainFilter() {
  try { localStorage.setItem(`${DOMAIN_FILTER_KEY}${configId.value}`, domainFilter.value) } catch { /* ignore */ }
}
function restoreDomainFilter() {
  try {
    const saved = localStorage.getItem(`${DOMAIN_FILTER_KEY}${configId.value}`)
    if (saved) domainFilter.value = saved
  } catch { /* ignore */ }
}
function extractDomains(items: any[]): string[] {
  const domains = new Set<string>()
  for (const item of items) {
    const d = item.domain || ''
    if (d) domains.add(d)
  }
  return Array.from(domains).sort()
}

// ── UI Mode / Density ──
const uiMode = ref<'browse' | 'edit'>('browse')
const compact = ref(uiMode.value === 'browse')
const showBaselineCol = ref(true)
const showLeftNav = computed(() => uiMode.value === 'browse')

// ── 测试项负责人单行编辑 ──
const ownerEditItemId = ref<number | null>(null)
const ownerEditValue = ref('')
const userOptions = ref<any[]>([])

async function loadUserOptions() {
  try {
    const res = await authApi.listUsers(1, 200)
    userOptions.value = res.data?.items || res.data || []
  } catch { userOptions.value = [] }
}

function canEditOwner(item: any): boolean {
  if (bom.archived || bom.review_status === 'pending') return false
  if (isSuperAdmin.value) return true
  return canEditItem(item)
}

function ownerTooltip(item: any): string {
  if (!item.owner_id && !item.owner_name) return '当前测试项未指定负责人'
  if (!isOtherOwned(item)) return '当前测试项由你负责'
  return `归属领域：${item.domain || '未知'}，负责人：${itemOwnerName(item)}，无编辑权限`
}

function startOwnerEdit(item: any) {
  ownerEditItemId.value = item.id
  ownerEditValue.value = itemOwnerName(item) || ''
}

function cancelOwnerEdit(item: any) {
  if (ownerEditItemId.value === item.id) ownerEditItemId.value = null
}

async function saveItemOwner(item: any) {
  const owner = String(ownerEditValue.value || '').trim()
  ownerEditItemId.value = null
  try {
    await metricsApi.updateCollectionItemOwner(item.id, owner)
    item.owner_name = owner || ''
    item.owner_manual = true
    if (owner) {
      const u = userOptions.value.find((x: any) => x.username === owner || x.display_name === owner)
      item.owner_id = u?.id ?? null
    } else {
      item.owner_id = null
    }
    ElMessage.success('测试项负责人已更新')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '更新负责人失败')
  }
}

function isOtherOwned(item: any): boolean {
  if (isBomCreator.value) return false
  if (!item.owner_id && !item.owner_name) return false
  if (item.owner_id) return item.owner_id !== currentUser.value?.id
  const me = currentUser.value?.username || currentUser.value?.display_name || ''
  return item.owner_name !== me
}

function itemBgClass(item: any): string {
  return isOtherOwned(item) ? 'bg-gray-100' : 'bg-white'
}

// ── WebSocket 协同编辑在线用户 ──
const onlineUsers = ref<any[]>([])
let bomWs: WebSocket | null = null
let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null

function getAvatarUrl(name: string): string {
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=random&color=fff&size=24`
}

function getCurrentUserId(): number {
  return currentUser.value?.id || 0
}

function getCurrentUserName(): string {
  return currentUser.value?.display_name || currentUser.value?.username || 'Unknown'
}

function connectBomWebSocket() {
  if (!bom.bom_code || !bom.version) return
  const wsUrl = `${import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'}/ws/bom/${bom.bom_code}/${bom.version}?user_id=${getCurrentUserId()}&user_name=${encodeURIComponent(getCurrentUserName())}`
  
  try {
    bomWs = new WebSocket(wsUrl)
    
    bomWs.onopen = () => {
      console.log('[BOM WS] Connected')
    }
    
    bomWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'online_users') {
          onlineUsers.value = msg.users || []
        } else if (msg.type === 'cursor') {
          // 可选：处理光标位置同步
        }
      } catch (e) {
        console.warn('[BOM WS] Parse error', e)
      }
    }
    
    bomWs.onclose = () => {
      console.log('[BOM WS] Disconnected, reconnecting in 5s...')
      if (wsReconnectTimer) clearTimeout(wsReconnectTimer)
      wsReconnectTimer = setTimeout(connectBomWebSocket, 5000)
    }
    
    bomWs.onerror = (err) => {
      console.error('[BOM WS] Error', err)
    }
  } catch (e) {
    console.error('[BOM WS] Connect error', e)
  }
}

function disconnectBomWebSocket() {
  if (bomWs) {
    bomWs.close()
    bomWs = null
  }
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer)
    wsReconnectTimer = null
  }
  onlineUsers.value = []
}

const emptyDescription = computed(() => {
  if (viewMode.value === 'empty') return '暂无未填写测试项'
  if (viewMode.value === 'filled') return '暂无已填写测试项'
  if (viewMode.value === 'diff') return '暂无与基准有差异的测试项'
  if (domainFilter.value !== '全部领域') return '当前领域下无测试项'
  return '该 BOM 暂未绑定测试项'
})

watch(uiMode, (mode) => {
  compact.value = mode === 'browse'
})
watch(domainFilter, () => {
  saveDomainFilter()
})

function fillProgress(): { filled: number; total: number; percent: number } {
  let total = 0, filled = 0
  for (const item of testItems.value) {
    for (const ind of item.indicatorList || []) {
      const params = ind._param_map || {}
      for (const p of Object.values(params)) {
        total++
        if ((p as any).value !== '' && (p as any).value !== null && (p as any).value !== undefined) filled++
      }
    }
  }
  return { filled, total, percent: total ? Math.round(filled / total * 100) : 0 }
}

const bomStats = computed(() => {
  let totalItems = 0, totalParams = 0, filledCount = 0, emptyCount = 0
  for (const item of testItems.value) {
    totalItems++
    for (const ind of item.indicatorList || []) {
      const params = ind._param_map || {}
      for (const p of Object.values(params)) {
        totalParams++
        if ((p as any).value !== '' && (p as any).value !== null && (p as any).value !== undefined) filledCount++
        else emptyCount++
      }
    }
  }
  return { totalItems, totalParams, filledCount, emptyCount }
})

// Filtered items based on viewMode
const filteredTestItems = computed(() => {
  if (viewMode.value === 'all') return testItems.value
  return testItems.value.map((item: any) => {
    const filteredIndicators = (item.indicatorList || []).filter((ind: any) => {
      const params = ind._param_map || {}
      if (viewMode.value === 'diff') {
        return Object.keys(params).some((k: string) => isParamDirty(ind.indicator_id, k))
      }
      const hasEmpty = Object.values(params).some((p: any) => p.value === '' || p.value === null || p.value === undefined)
      const hasFilled = Object.values(params).some((p: any) => p.value !== '' && p.value !== null && p.value !== undefined)
      if (viewMode.value === 'empty') return hasEmpty
      if (viewMode.value === 'filled') return hasFilled
      return true
    })
    return { ...item, indicatorList: filteredIndicators }
  }).filter(item => (item.indicatorList || []).length > 0)
})

const processFilter = ref('')

const processStationGroups = computed(() => {
  const groups: Record<string, Record<string, any[]>> = {}
  for (const item of filteredTestItems.value) {
    const proc = item.process_name || '未分类工序'
    const sta = item.station_name || '通用工位'
    if (!groups[proc]) groups[proc] = {}
    if (!groups[proc][sta]) groups[proc][sta] = []
    groups[proc][sta].push(item)
  }
  return groups
})

// Numeric-aware ascending compare so 工位2 < 工位10
function naturalCompare(a: string, b: string): number {
  return a.localeCompare(b, 'zh-CN', { numeric: true })
}

const processOptions = computed(() => Object.keys(processStationGroups.value))
const stationOptions = computed(() => {
  if (!processFilter.value) return [] as string[]
  const staMap = processStationGroups.value[processFilter.value]
  return staMap ? Object.keys(staMap).sort(naturalCompare) : []
})

const filteredProcessStationGroups = computed(() => {
  const groups = processStationGroups.value
  if (!processFilter.value && !stationFilter.value) return groups
  const result: Record<string, Record<string, any[]>> = {}
  for (const [proc, staMap] of Object.entries(groups)) {
    if (processFilter.value && proc !== processFilter.value) continue
    for (const [sta, items] of Object.entries(staMap)) {
      if (stationFilter.value && sta !== stationFilter.value) continue
      if (!result[proc]) result[proc] = {}
      result[proc][sta] = items
    }
  }
  return result
})

// 3-level tree: process → station → items
 const processTreeData = computed(() => {
   const filtered = Object.entries(filteredProcessStationGroups.value).map(([procName, staMap]) => {
     const stations = Object.entries(staMap)
       .sort(([a], [b]) => naturalCompare(a, b))
       .map(([staName, items]) => {
         const filteredItems = domainFilter.value === '全部领域' ? items : items.filter((item: any) => item.domain === domainFilter.value)
         const staTotal = filteredItems.reduce((s: number, item: any) => s + (item.indicatorList || []).reduce((s2: number, ind: any) => s2 + Object.keys(ind._param_map || {}).length, 0), 0)
         const staEmpty = filteredItems.reduce((s: number, item: any) => s + (item.indicatorList || []).reduce((s2: number, ind: any) => {
           const params = ind._param_map || {}
           return s2 + Object.values(params).filter((p: any) => p.value === '' || p.value === null || p.value === undefined).length
         }, 0), 0)
         const staDiff = filteredItems.reduce((s: number, item: any) => s + diffCountForItem(item), 0)
         return { name: staName, items: filteredItems, totalParams: staTotal, emptyParams: staEmpty, diffCount: staDiff }
       })
       .filter((s: any) => s.items.length > 0)
     const allItems = stations.flatMap((s: any) => s.items)
     const totalParams = allItems.reduce((sum: number, item: any) => sum + (item.indicatorList || []).reduce((s: number, ind: any) => s + Object.keys(ind._param_map || {}).length, 0), 0)
     const emptyParams = allItems.reduce((sum: number, item: any) => sum + (item.indicatorList || []).reduce((s: number, ind: any) => {
       const params = ind._param_map || {}
       return s + Object.values(params).filter((p: any) => p.value === '' || p.value === null || p.value === undefined).length
     }, 0), 0)
     const procDiff = stations.reduce((s: number, st: any) => s + (st.diffCount || 0), 0)
     return { name: procName, stations, totalParams, emptyParams, diffCount: procDiff }
   }).filter((p: any) => p.stations.length > 0)
   return filtered
 })

function diffCountForItem(item: any): number {
  let count = 0
  for (const ind of item.indicatorList || []) {
    const map = ind._param_map || {}
    for (const key of Object.keys(map)) {
      const bv = baselineParams.value[ind.indicator_id + '#' + key]
      if (bv !== undefined && String(map[key].value ?? '') !== bv) count++
    }
  }
  return count
}

// Search-filtered tree for left nav
const filteredProcessTree = computed(() => {
  if (!processSearch.value) return processTreeData.value
  const q = processSearch.value.toLowerCase()
  const result: any[] = []
  for (const proc of processTreeData.value) {
    const matchedStations = proc.stations.filter((sta: any) =>
      sta.name.toLowerCase().includes(q) ||
      sta.items.some((it: any) => it.name.toLowerCase().includes(q))
    )
    if (proc.name.toLowerCase().includes(q)) {
      result.push(proc)
    } else if (matchedStations.length) {
      result.push({ ...proc, stations: matchedStations })
    }
  }
  return result
})

function onTreeSearch() {
  if (processSearch.value && processTreeData.value.length) {
    const firstMatch = filteredProcessTree.value[0]
    if (firstMatch && !expandedProcesses.value.includes(firstMatch.name)) {
      expandedProcesses.value = [firstMatch.name]
    }
  }
}

// ── Left nav: station folding + item rendering ──
const navStationKeys = ref<string[]>([])

function isNavStationExpanded(procName: string, staName: string): boolean {
  return navStationKeys.value.includes(procName + '::' + staName)
}

function toggleNavStation(procName: string, staName: string) {
  const key = procName + '::' + staName
  const idx = navStationKeys.value.indexOf(key)
  if (idx >= 0) navStationKeys.value.splice(idx, 1)
  else navStationKeys.value.push(key)
}

watch(expandedProcesses, (procs) => {
  const keys: string[] = []
  for (const procName of procs) {
    const proc = processTreeData.value.find(p => p.name === procName)
    if (proc) {
      for (const sta of proc.stations) keys.push(procName + '::' + sta.name)
    }
  }
  navStationKeys.value = keys
})

function itemDiffCount(item: any): number {
  return diffCountForItem(item)
}

function itemEmptyCount(item: any): number {
  let count = 0
  for (const ind of item.indicatorList || []) {
    const map = ind._param_map || {}
    for (const key of Object.keys(map)) {
      const v = map[key].value
      if (v === '' || v === null || v === undefined) count++
    }
  }
  return count
}

function navItemClass(item: any): string {
  if (isSelectedItem(item) || navItemId.value === item.id) return 'bg-blue-50 text-blue-600 font-medium'
  if (itemHasDiff(item)) return 'text-amber-600 hover:bg-amber-50'
  if (hasEmptyParams(item)) return 'text-red-500 hover:bg-red-50'
  return 'text-gray-700 hover:bg-gray-100'
}

// ── Content-level Expand/Collapse controls ──
function allStationKeys(): string[] {
  const keys: string[] = []
  for (const proc of processTreeData.value) {
    for (const sta of proc.stations) keys.push(proc.name + '::' + sta.name)
  }
  return keys
}

function expandAllContent() {
  expandedProcesses.value = processTreeData.value.map(p => p.name)
  expandedStations.value = allStationKeys()
  ElMessage.success('已全部展开')
}

function collapseAllContent() {
  expandedProcesses.value = []
  expandedStations.value = []
}

function itemHasDiff(item: any): boolean {
  return (item.indicatorList || []).some((ind: any) =>
    Object.keys(ind._param_map || {}).some((k: string) => isParamDirty(ind.indicator_id, k))
  )
}

function expandOnlyDiff() {
  if (!Object.keys(baselineParams.value).length) {
    ElMessage.warning('暂无基准差异数据，请先点击「对比基准发布版本」')
    return
  }
  const procs: string[] = []
  const stas: string[] = []
  for (const proc of processTreeData.value) {
    for (const sta of proc.stations) {
      if (sta.items.some((it: any) => itemHasDiff(it))) {
        stas.push(proc.name + '::' + sta.name)
        if (!procs.includes(proc.name)) procs.push(proc.name)
      }
    }
  }
  expandedProcesses.value = procs
  expandedStations.value = stas
  ElMessage.info(procs.length ? `已展开 ${procs.length} 个含差异工序` : '当前无差异项')
}

function getItemParamPreview(item: any): string {
  const cols = item._param_cols || item.indicatorList?.[0]?._param_cols || []
  const ind = item.indicatorList?.[0]
  if (!ind || !cols.length) return '暂无参数'
  return cols.map((pc: any) => `${pc.label}: ${ind._param_map?.[pc.key]?.value ?? '-'}`).join(' | ')
}

// ── Helper Functions ──

// ── 协同编辑：负责人权限判断 ──
function itemOwnerName(item: any): string {
  return item.owner_name || item.owner || ''
}

function canEditItem(item: any): boolean {
  if (isSuperAdmin.value) return true
  if (isBomCreator.value) return true
  if (bom.archived || bom.review_status === 'pending') return false
  if (!item.owner_id && !item.owner_name) return true
  if (item.owner_id) return item.owner_id === currentUser.value?.id
  // 负责人仅有名称（用户可能不存在于用户表），按名称兜底匹配
  const me = currentUser.value?.username || currentUser.value?.display_name || ''
  return item.owner_name === me
}

function itemReadonlyReason(item: any): string {
  if (bom.archived) return 'BOM 已归档，禁止编辑'
  if (bom.review_status === 'pending') return 'BOM 评审中，禁止编辑'
  const owner = itemOwnerName(item)
  if (isOtherOwned(item)) {
    return `归属领域：${item.domain || '未知'}，负责人：${owner || '他人'}，无编辑权限`
  }
  return ''
}

function hasEmptyParams(item: any): boolean {
  return (item.indicatorList || []).some((ind: any) => {
    const params = ind._param_map || {}
    return Object.values(params).some((p: any) => p.value === '' || p.value === null || p.value === undefined)
  })
}

function itemHasParams(item: any): boolean {
  return getItemParamRows(item).length > 0
}

function getItemParamRows(item: any): any[] {
  const cols = item._param_cols || item.indicatorList?.[0]?._param_cols || []
  const seen = new Set<string>()
  const rows: any[] = []
  for (const ind of item.indicatorList || []) {
    for (const pc of cols) {
      const key = ind.indicator_id + '#' + pc.key
      if (seen.has(key)) continue
      seen.add(key)
      rows.push({
        _ind: ind,
        _item: item,
        indicator_id: ind.indicator_id,
        _bom_indicator_id: ind._bom_indicator_id,
        param_key: pc.key,
        label: pc.label,
        format: pc.format,
        required: pc.required,
        remark: pc.remark,
        min_width: pc.minWidth,
      })
    }
  }
  return rows
}

function isParamEmpty(ind: any, paramKey: string): boolean {
  const val = ind._param_map?.[paramKey]?.value
  return val === '' || val === null || val === undefined
}

function paramFormatLabel(format: string): string {
  const map: Record<string, string> = {
    number: '数字',
    range: '范围（数字）',
    percent: '百分比',
    boolean: '布尔（true/false）',
    array: '数组（英文逗号分隔）',
    list: '列表（英文逗号分隔）',
    string: '字符串',
    text: '文本',
    enum: '枚举',
    expr: '表达式',
  }
  return map[format] || format || '未知'
}

function startInlineEdit(row: any) {
  if (bom.archived || bom.review_status === 'pending') return
  const item = row._item
  if (item && !canEditItem(item)) return
  if (isListFormat(row.format)) {
    openListEditor(row)
    return
  }
  editParamKey.value = row._bom_indicator_id + '#val#' + row.param_key
}

// ── List-format param: truncated display + dialog editing ──
const listEditDialog = reactive({ visible: false, saving: false, label: '', format: '', indicator: null as any, paramKey: '' as string, value: '' })

function isListFormat(format: string): boolean {
  return format === 'array' || format === 'list'
}

function listDisplay(row: any): string {
  const val = row._ind._param_map?.[row.param_key]?.value
  if (val === '' || val === null || val === undefined) return '-'
  return String(val)
}

function openListEditor(row: any) {
  if (bom.archived || bom.review_status === 'pending') return
  const item = row._item
  if (item && !canEditItem(item)) return
  editParamKey.value = ''
  listEditDialog.visible = true
  listEditDialog.label = row.label
  listEditDialog.format = row.format
  listEditDialog.indicator = row._ind
  listEditDialog.paramKey = row.param_key
  listEditDialog.value = String(row._ind._param_map?.[row.param_key]?.value ?? '')
}

async function saveListEditor() {
  if (!listEditDialog.indicator) return
  const raw = String(listEditDialog.value || '')
  const normalized = raw
    .replace(/，/g, ',')
    .split(/[\n,]+/)
    .map((s: string) => s.trim())
    .filter((s: string) => s !== '')
    .join(',')
  const ind = listEditDialog.indicator
  const key = listEditDialog.paramKey
  ind._param_map[key].value = normalized
  listEditDialog.visible = false
  saveDraft()
  await validateAndSaveParam(ind, key)
  if (normalized) ElMessage.success('已保存列表参数')
}

// ── Copy baseline value to current edit ──
async function copyBaselineValue(row: any) {
  if (row._item && !canEditItem(row._item)) {
    ElMessage.warning('该测试项无编辑权限')
    return
  }
  const bv = baselineParams.value[row.indicator_id + '#' + row.param_key]
  if (bv === undefined) return
  row._ind._param_map[row.param_key].value = bv
  saveDraft()
  await saveParamValue(row._ind, row.param_key)
  ElMessage.success('已复制归档基准原值')
}

// ── Inline edit: Tab to switch between params ──
function onInlineEditKeydown(e: KeyboardEvent, row: any, item: any) {
  if (e.key !== 'Tab') return
  e.preventDefault()
  const rows = getItemParamRows(item)
  const idx = rows.findIndex((r: any) => r._ind === row._ind && r.param_key === row.param_key)
  let next = e.shiftKey ? idx - 1 : idx + 1
  while (next >= 0 && next < rows.length && isListFormat(rows[next].format)) {
    next = e.shiftKey ? next - 1 : next + 1
  }
  if (next < 0 || next >= rows.length) return
  const nr = rows[next]
  editParamKey.value = nr._bom_indicator_id + '#val#' + nr.param_key
  nextTick(() => {
    const input = document.querySelector('.param-cell .el-input__inner') as HTMLInputElement | null
    input?.focus()
  })
}

function paramRowClass({ row }: any): string {
  const val = row._ind._param_map?.[row.param_key]?.value
  const empty = val === '' || val === null || val === undefined
  return empty ? 'param-empty-row' : ''
}

function emptyParamCount(item: any): number {
  let count = 0
  for (const ind of item.indicatorList || []) {
    const params = ind._param_map || {}
    for (const p of Object.values(params) as any[]) {
      if (p.value === '' || p.value === null || p.value === undefined) count++
    }
  }
  return count
}

function tableRowClassName({ row }: any): string {
  const params = row._param_map || {}
  const hasEmpty = Object.values(params).some((p: any) => p.value === '' || p.value === null || p.value === undefined)
  return hasEmpty ? 'param-empty-row' : ''
}

const expandedStations = ref<string[]>([]) // keys: "processName::stationName"

const hasAutoExpanded = ref(false)

function autoExpandFirstEmptyStation() {
  const val = processTreeData.value
  if (!val.length) return
  const keys: string[] = []
  for (const proc of val) {
    for (const sta of proc.stations) {
      if (sta.emptyParams > 0) {
        keys.push(proc.name + '::' + sta.name)
        if (keys.length === 1) break // only expand first empty station
      }
    }
    if (keys.length) break
  }
  // If all filled, expand first station
  if (!keys.length && val[0]?.stations.length) {
    keys.push(val[0].name + '::' + val[0].stations[0].name)
  }
  expandedStations.value = keys
}

function isStationExpanded(procName: string, staName: string): boolean {
  return expandedStations.value.includes(procName + '::' + staName)
}
function toggleStationExpand(procName: string, staName: string) {
  const key = procName + '::' + staName
  const idx = expandedStations.value.indexOf(key)
  if (idx >= 0) {
    expandedStations.value.splice(idx, 1)
  } else {
    expandedStations.value.push(key)
    // Lazy-load station draft cache on expand
    restoreStationDraft(procName, staName)
  }
}

function scrollToStaItem(itemId: number, _staName: string) {
  const el = document.getElementById(`item-${itemId}`)
  if (el) {
    const procEl = el.closest('[data-process]')
    if (procEl) {
      const procName = procEl.getAttribute('data-process')
      if (procName && !expandedProcesses.value.includes(procName)) {
        expandedProcesses.value.push(procName)
      }
    }
    const staEl = el.closest('[data-station]')
    if (staEl && procEl) {
      const staName = staEl.getAttribute('data-station')
      const pn = procEl.getAttribute('data-process') || ''
      if (staName && !isStationExpanded(pn, staName)) toggleStationExpand(pn, staName)
    }
    scrollItemIntoView(itemId)
  }
}

function scrollToItem(itemId: number) {
  const el = document.getElementById(`item-${itemId}`)
  if (el) {
    const procEl = el.closest('[data-process]')
    if (procEl) {
      const procName = procEl.getAttribute('data-process')
      if (procName && !expandedProcesses.value.includes(procName)) {
        expandedProcesses.value.push(procName)
      }
    }
    const staEl = el.closest('[data-station]')
    if (staEl && procEl) {
      const staName = staEl.getAttribute('data-station')
      const pn = procEl.getAttribute('data-process') || ''
      if (staName && !isStationExpanded(pn, staName)) toggleStationExpand(pn, staName)
    }
    scrollItemIntoView(itemId)
  }
}

function copyPrevStation(procName: string, staName: string) {
  const proc = processTreeData.value.find(p => p.name === procName)
  if (!proc) return
  const staIdx = proc.stations.findIndex(s => s.name === staName)
  if (staIdx <= 0) { ElMessage.warning('没有上一个工位可复制'); return }
  const sourceItems = proc.stations[staIdx - 1].items
  const targetItems = proc.stations[staIdx].items
  for (const target of targetItems) {
    const source = sourceItems.find((s: any) => s.name === target.name)
    if (source) {
      for (const targetInd of target.indicatorList || []) {
        const sourceInd = source.indicatorList?.find((s: any) => s.indicator_id === targetInd.indicator_id)
        if (sourceInd) {
          targetInd._param_map = JSON.parse(JSON.stringify(sourceInd._param_map || {}))
        }
      }
    }
  }
  ElMessage.success(`已复制上工位参数至 ${targetItems.length} 个测试项`)
  saveDraft()
}

async function copyPrevProcess(targetProcessName: string) {
  const procIndex = processTreeData.value.findIndex(p => p.name === targetProcessName)
  if (procIndex <= 0) { ElMessage.warning('没有上一个工序可复制'); return }
  const sourceName = processTreeData.value[procIndex - 1].name
  try {
    await ElMessageBox.confirm(
      `确认将工序「${sourceName}」的参数复制到当前工序「${targetProcessName}」？`,
      '跨工序复制确认',
      { type: 'warning', confirmButtonText: '确认复制', cancelButtonText: '取消' }
    )
  } catch { return }
  const sourceStations = processTreeData.value[procIndex - 1].stations
  const targetStations = processTreeData.value[procIndex].stations
  for (let si = 0; si < targetStations.length && si < sourceStations.length; si++) {
    const sourceItems = sourceStations[si].items
    const targetItems = targetStations[si].items
    for (const target of targetItems) {
      const source = sourceItems.find((s: any) => s.name === target.name)
      if (source) {
        for (const targetInd of target.indicatorList || []) {
          const sourceInd = source.indicatorList?.find((s: any) => s.indicator_id === targetInd.indicator_id)
          if (sourceInd) {
            targetInd._param_map = JSON.parse(JSON.stringify(sourceInd._param_map || {}))
          }
        }
      }
    }
  }
  ElMessage.success(`已复制上工序参数`)
  saveDraft()
}

async function clearStationParams(procName: string, staName: string) {
  try {
    await ElMessageBox.confirm(`确定清空「${procName} / ${staName}」下所有参数？此操作不可撤销`, '确认清空', { type: 'warning' })
    const proc = processTreeData.value.find(p => p.name === procName)
    if (!proc) return
    const sta = proc.stations.find(s => s.name === staName)
    if (sta) {
      for (const item of sta.items) {
        for (const ind of item.indicatorList || []) {
          const params = ind._param_map || {}
          for (const p of Object.values(params)) { (p as any).value = '' }
        }
      }
      const ok = await saveAllPendingParams()
      if (ok) ElMessage.success(`已清空「${procName} / ${staName}」下所有参数`)
    }
  } catch { /* cancelled */ }
}

async function batchFillStation(procName: string, staName: string) {
  try {
    const { value: upper } = await ElMessageBox.prompt('上限值（留空不填）', `批量填充工位「${staName}」`, {
      inputType: 'text', inputPlaceholder: '上限值',
    })
    const { value: lower } = await ElMessageBox.prompt('下限值（留空不填）', `批量填充工位「${staName}」`, {
      inputType: 'text', inputPlaceholder: '下限值',
    })
    for (const proc of processTreeData.value) {
      if (proc.name !== procName) continue
      for (const sta of proc.stations) {
        if (sta.name !== staName) continue
        for (const item of sta.items) {
          for (const ind of item.indicatorList || []) {
            const params = ind._param_map || {}
            for (const [key, info] of Object.entries(params) as [string, any][]) {
              if (['number', 'range', 'percent'].includes(info.format)) {
                if (upper) info.value = upper
                if (lower) info.value = lower
              }
            }
          }
        }
      }
    }
    const ok = await saveAllPendingParams()
    if (ok) ElMessage.success(`已批量填充工位「${staName}」`)
  } catch { /* cancelled */ }
}

function exportStationExcel(procName: string, staName: string) {
  rightToolbar.exportProcessName = procName
  rightToolbar.exportStationName = staName
  exportCurrentConfig()
}

async function syncStationFromHistory(procName: string, staName: string) {
  try {
    await ElMessageBox.confirm(`从历史版本同步工位「${staName}」的参数？当前已修改的值将被覆盖。`, '同步历史参数', { type: 'warning' })
    // Load published versions and diff
    await loadPublishedVersions(configId.value)
    if (!diffDialog.publishedVersions.length) {
      ElMessage.info('无已发布版本可供同步')
      return
    }
    diffDialog.selectedSnapshotId = diffDialog.publishedVersions[0].id
    await loadArchivedDiff()
    // Apply archived values to the station's indicators
    for (const mod of diffDialog.modified) {
      if (mod.station_name !== staName) continue
      const indicatorName = mod.indicatorName
      const paramName = mod.paramName
      for (const proc of processTreeData.value) {
        if (proc.name !== procName) continue
        for (const sta of proc.stations) {
          if (sta.name !== staName) continue
          for (const item of sta.items) {
            for (const ind of item.indicatorList || []) {
              if ((ind.name || ind.code) !== indicatorName) continue
              for (const [key, info] of Object.entries(ind._param_map || {}) as [string, any][]) {
                if (info.name === paramName || key === paramName) {
                  info.value = mod.oldValue
                }
              }
            }
          }
        }
      }
    }
    const ok = await saveAllPendingParams()
    if (ok) ElMessage.success(`已同步工位「${staName}」的历史参数`)
  } catch { /* cancelled */ }
}

async function batchFillProcess(processName: string) {
  try {
    const { value: form } = await ElMessageBox.prompt('请输入上限值（留空则不填上限）', `批量填充工序「${processName}」`, {
      inputType: 'text', inputPlaceholder: '上限值（数字）', inputValue: rightToolbar.batchFillThreshold.upper,
    })
    const { value: lowerForm } = await ElMessageBox.prompt('请输入下限值（留空则不填下限）', `批量填充工序「${processName}」`, {
      inputType: 'text', inputPlaceholder: '下限值（数字）',
    })
    const upper = form || ''
    const lower = lowerForm || ''
    for (const proc of processTreeData.value) {
      if (proc.name === processName) {
        for (const sta of proc.stations) {
          for (const item of sta.items) {
            for (const ind of item.indicatorList || []) {
              const params = ind._param_map || {}
              for (const [key, info] of Object.entries(params) as [string, any][]) {
                if (['number', 'range', 'percent'].includes(info.format)) {
                  if (upper) info.value = upper
                  if (lower) info.value = lower
                }
              }
            }
          }
        }
      }
    }
    const ok = await saveAllPendingParams()
    if (ok) ElMessage.success(`已批量填充工序「${processName}」`)
  } catch { /* cancelled */ }
}

async function clearProcessParams(processName: string) {
  try {
    await ElMessageBox.confirm(`确定清空工序「${processName}」下所有测试项的参数？此操作不可撤销`, '确认清空', { type: 'warning' })
    for (const proc of processTreeData.value) {
      if (proc.name === processName) {
        for (const sta of proc.stations) {
          for (const item of sta.items) {
            for (const ind of item.indicatorList || []) {
              const params = ind._param_map || {}
              for (const p of Object.values(params)) { (p as any).value = '' }
            }
          }
        }
      }
    }
    const ok = await saveAllPendingParams()
    if (ok) ElMessage.success(`已清空工序「${processName}」下所有参数`)
  } catch { /* cancelled */ }
}

// ── Item Selection ──
function isSelectedItem(item: any): boolean {
  return rightToolbar.selectedItems.some(si => si.indicator_id === item.indicatorList?.[0]?.indicator_id)
}

function scrollItemIntoView(itemId: number) {
  nextTick(() => {
    const el = document.getElementById(`item-${itemId}`)
    if (!el) return
    const scroller = (el.closest('.el-main') || document.scrollingElement) as HTMLElement
    const sr = scroller.getBoundingClientRect()
    const er = el.getBoundingClientRect()
    const target = scroller.scrollTop + (er.top - sr.top) - (sr.height - er.height) / 2
    try {
      scroller.scrollTo({ top: Math.max(0, target), behavior: 'smooth' })
    } catch {
      scroller.scrollTop = Math.max(0, target)
    }
  })
}

function applyItemFocus(item: any, procName: string, staName: string, toggle: boolean) {
  // Always expand parents and scroll, even if the item has no indicators
  if (!expandedProcesses.value.includes(procName)) {
    expandedProcesses.value.push(procName)
  }
  if (!isStationExpanded(procName, staName)) {
    toggleStationExpand(procName, staName)
  }
  const indicators = item.indicatorList || []
  if (indicators.length) {
    if (toggle && isSelectedItem(item)) {
      rightToolbar.selectedItems = []
    } else {
      rightToolbar.selectedItems = indicators.map((ind: any) => ({
        ...ind,
        _item_name: item.name,
        _process_name: procName,
        _station_name: staName,
        _param_cols: item._param_cols || ind._param_cols || [],
      }))
    }
  }
  scrollItemIntoView(item.id)
  // Keep the clicked item visible within the left nav card only
  keepNavItemVisible(item.id)
}

function selectItem(item: any, procName: string, staName: string) {
  navItemId.value = item.id
  applyItemFocus(item, procName, staName, true)
}

// ── Keyboard Up/Down navigation across items ──
function getAllNavEntries(): { item: any; process: string; station: string }[] {
  const entries: { item: any; process: string; station: string }[] = []
  for (const proc of processTreeData.value) {
    for (const sta of proc.stations) {
      for (const item of sta.items) {
        entries.push({ item, process: proc.name, station: sta.name })
      }
    }
  }
  return entries
}

function focusItemByOffset(offset: 1 | -1) {
  const entries = getAllNavEntries()
  if (!entries.length) return
  let idx = navItemId.value != null ? entries.findIndex(en => en.item.id === navItemId.value) : -1
  if (idx === -1) {
    idx = offset === 1 ? 0 : entries.length - 1
  } else {
    idx = Math.max(0, Math.min(entries.length - 1, idx + offset))
  }
  const entry = entries[idx]
  navItemId.value = entry.item.id
  applyItemFocus(entry.item, entry.process, entry.station, false)
}

function handleNavKeydown(e: KeyboardEvent) {
  if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
  const target = e.target as HTMLElement
  if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return
  if (e.altKey || e.ctrlKey || e.metaKey) return
  e.preventDefault()
  focusItemByOffset(e.key === 'ArrowDown' ? 1 : -1)
}

function keepNavItemVisible(itemId: number) {
  nextTick(() => {
    const navBtn = document.querySelector(`[data-nav-item="${itemId}"]`) as HTMLElement | null
    const card = (navCardRef.value?.$el ?? navCardRef.value) as HTMLElement | null
    if (!navBtn || !card || typeof card.getBoundingClientRect !== 'function') return
    const cRect = card.getBoundingClientRect()
    const bRect = navBtn.getBoundingClientRect()
    if (bRect.top < cRect.top || bRect.bottom > cRect.bottom) {
      const target = card.scrollTop + (bRect.top - cRect.top) - (cRect.height - bRect.height) / 2
      try {
        card.scrollTo({ top: Math.max(0, target), behavior: 'smooth' })
      } catch {
        card.scrollTop = Math.max(0, target)
      }
    }
  })
}

function copySelectedItems() {
  rightToolbar.copySourceItems = rightToolbar.selectedItems.map(item => ({
    indicator_id: item.indicator_id,
    process_name: item.process_name || '',
    station_name: item.station_name || '',
    params: JSON.parse(JSON.stringify(item._param_map || {}))
  }))
  ElMessage.success(`已复制 ${rightToolbar.copySourceItems.length} 个测试项的参数`)
}

async function pasteToSelected() {
  if (!rightToolbar.copySourceItems.length) { ElMessage.warning('请先复制参数'); return }
  // Check if any target is cross-station
  const crossStationItems = rightToolbar.selectedItems.filter(target => {
    const source = rightToolbar.copySourceItems.find(s => s.indicator_id === target.indicator_id)
    return source && (source.process_name !== (target.process_name || '') || source.station_name !== (target.station_name || ''))
  })
  if (crossStationItems.length > 0) {
    try {
      await ElMessageBox.confirm(
        `有 ${crossStationItems.length} 个测试项跨越工序/工位（来源与目标不符），确认继续粘贴？`,
        '跨工位操作确认',
        { type: 'warning', confirmButtonText: '确认粘贴', cancelButtonText: '取消' }
      )
    } catch { return }
  }
  for (const target of rightToolbar.selectedItems) {
    const source = rightToolbar.copySourceItems.find(s => s.indicator_id === target.indicator_id)
    if (source) {
      target._param_map = JSON.parse(JSON.stringify(source.params))
    }
  }
  const ok = await saveAllPendingParams()
  if (ok) ElMessage.success(`已粘贴到 ${rightToolbar.selectedItems.length} 个测试项`)
}

function clearSelectedParams() {
  for (const item of rightToolbar.selectedItems) {
    const params = item._param_map || {}
    for (const p of Object.values(params)) { (p as any).value = '' }
  }
  saveAllPendingParams()
  ElMessage.success(`已清空 ${rightToolbar.selectedItems.length} 个测试项的参数`)
  rightToolbar.selectedItems = []
}

function filterEmptyParams() {
  viewMode.value = 'empty'
  ElMessage.info('已切换到未填写视图')
}

function isProcessExpanded(name: string): boolean {
  return expandedProcesses.value.includes(name)
}

function toggleProcessExpand(name: string) {
  const idx = expandedProcesses.value.indexOf(name)
  if (idx >= 0) expandedProcesses.value.splice(idx, 1)
  else expandedProcesses.value.push(name)
}

const editRowId = ref(0)
const editField = ref('')
const editParamKey = ref('')

const exportDialog = reactive({ visible: false, format: 'json' })
const exporting = ref(false)

// ── Excel Import Dialog ──
const importDialog = reactive({ visible: false, loading: false })
const importResult = ref<any>(null)

// ── Pre-save Validation ──
const validationDialog = reactive({ visible: false, loading: false })
const validationResult = ref<any>(null)
const validationErrors = ref<any>([])
const validationError = ref('')
function onValidationOpen() {
  validationError.value = ''
}

const diffDialog = reactive({
  visible: false, loading: false,
  bomCode: '',
  selectedSnapshotId: 0 as any,
  publishedVersions: [] as any[],
  showAllVersions: false,
  added: { newItems: [] as any[], newParams: [] as any[] },
  removed: { deletedItems: [] as any[], deletedParams: [] as any[] },
  modified: [] as any[],
})

// All published/archived BOM snapshots across every BOM (the "archived database")
const archivedSnapshots = ref<any[]>([])

// A version number maps to a single published storage (keep the latest snapshot per version)
function dedupVersions(list: any[]): any[] {
  const map = new Map<number, any>()
  for (const v of list) {
    const ver = v.version
    if (!map.has(ver) || (map.get(ver).id || 0) < (v.id || 0)) map.set(ver, v)
  }
  return Array.from(map.values()).sort((a: any, b: any) => (b.version || 0) - (a.version || 0))
}

const bomCodeSnapshots = computed(() => {
  const code = (diffDialog.bomCode || '').trim()
  if (!code) return []
  return dedupVersions(
    archivedSnapshots.value.filter((s: any) => (s.snapshot_data?.bom_config?.bom_code || '') === code)
  )
})

// Show at most 5 version options in the dropdown; the rest are reachable via expand
const versionOptions = computed(() => {
  const list = diffDialog.publishedVersions
  if (list.length <= 5) return list
  if (diffDialog.showAllVersions) {
    return list.concat([{ id: '__less__', version: -1, _less: true }])
  }
  return list.slice(0, 5).concat([{ id: '__more__', version: -1, _more: true, _hidden: list.length - 5 }])
})

function versionOptionLabel(v: any): string {
  if (v._more) return `展开更多（${v._hidden}）`
  if (v._less) return '收起'
  return `v${v.version}`
}

// ── Per-station sharded draft cache (localStorage) ──
const STATION_DIRTY = new Set<string>()

function stationCacheKey(procName: string, staName: string): string {
  return `${STORAGE_KEY}${configId.value}_${procName}::${staName}`
}

function markStationDirty(procName: string, staName: string) {
  STATION_DIRTY.add(stationCacheKey(procName, staName))
}

function saveStationDraft(procName: string, staName: string) {
  const key = stationCacheKey(procName, staName)
  const data: Record<string, any> = {}
  for (const proc of processTreeData.value) {
    if (proc.name !== procName) continue
    for (const sta of proc.stations) {
      if (sta.name !== staName) continue
      for (const item of sta.items) {
        for (const ind of item.indicatorList || []) {
          const map = ind._param_map || {}
          for (const pk of Object.keys(map)) {
            data[ind.indicator_id + '#' + pk] = map[pk].value
          }
        }
      }
    }
  }
  localStorage.setItem(key, JSON.stringify(data))
  STATION_DIRTY.delete(key)
}

function restoreStationDraft(procName: string, staName: string) {
  const key = stationCacheKey(procName, staName)
  const raw = localStorage.getItem(key)
  if (!raw) return
  try {
    const data = JSON.parse(raw)
    for (const proc of processTreeData.value) {
      if (proc.name !== procName) continue
      for (const sta of proc.stations) {
        if (sta.name !== staName) continue
        for (const item of sta.items) {
          for (const ind of item.indicatorList || []) {
            const map = ind._param_map || {}
            for (const pk of Object.keys(map)) {
              const stored = data[ind.indicator_id + '#' + pk]
              if (stored !== undefined) {
                map[pk].value = stored
              }
            }
          }
        }
      }
    }
  } catch { /* ignore corrupt cache */ }
}

function versionStatusText(bom: any): string {
  if (bom.archived) return '已归档'
  if (bom.review_status === 'approved') return '已发布'
  if (bom.review_status === 'pending') return '评审中'
  if (bom.review_status === 'rejected') return '已驳回'
  return '未评审'
}

function saveDraft(procName?: string, staName?: string) {
  if (procName && staName) {
    saveStationDraft(procName, staName)
    return
  }
  // Save all stations (detect dirty from tree data)
  for (const proc of processTreeData.value) {
    for (const sta of proc.stations) {
      saveStationDraft(proc.name, sta.name)
    }
  }
}

function restoreDraft() {
  // Restore all cached stations by scanning localStorage
  const prefix = `${STORAGE_KEY}${configId.value}_`
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key?.startsWith(prefix)) {
      const rest = key.slice(prefix.length)
      const sepIdx = rest.indexOf('::')
      if (sepIdx > 0) {
        const pn = rest.slice(0, sepIdx)
        const sn = rest.slice(sepIdx + 2)
        restoreStationDraft(pn, sn)
      }
    }
  }
}

function clearDraft() {
  const prefix = `${STORAGE_KEY}${configId.value}_`
  for (let i = localStorage.length - 1; i >= 0; i--) {
    const key = localStorage.key(i)
    if (key?.startsWith(prefix)) {
      localStorage.removeItem(key)
    }
  }
  STATION_DIRTY.clear()
}

// ── Baseline diff state ──
const baselineVersions = ref<any[]>([])
const baselineParams = ref<Record<string, string>>({}) // "indicatorId#paramKey" → baseline value

async function loadBaselineParams() {
  try {
    const diffRes = await metricsApi.diffBaseline(configId.value)
    const data = diffRes.data
    if (!data?.has_baseline) {
      baselineParams.value = {}
      return
    }
    const snapshotRes = await metricsApi.getVersionDetail(data.baseline_snapshot_id)
    const snapshot = snapshotRes.data?.snapshot_data
    if (!snapshot) {
      baselineParams.value = {}
      return
    }
    const indicators = snapshot.indicators || []
    const map: Record<string, string> = {}
    for (const ind of indicators) {
      const params = ind.params || []
      for (const p of params) {
        const key = p.key || p.param_key
        if (key) {
          map[ind.indicator_id + '#' + key] = String(p.value ?? p.param_value ?? '')
        }
      }
    }
    baselineParams.value = map
  } catch {
    baselineParams.value = {}
  }
}

function isParamDirty(indicatorId: number, paramKey: string): boolean {
  if (!Object.keys(baselineParams.value).length) return false
  const bv = baselineParams.value[indicatorId + '#' + paramKey]
  if (bv === undefined) return false
  // find current value
  for (const item of testItems.value) {
    for (const ind of item.indicatorList || []) {
      if (ind.indicator_id === indicatorId) {
        return String(ind._param_map?.[paramKey]?.value ?? '') !== bv
      }
    }
  }
  return false
}

// ── Load Data ──
async function loadAll() {
  loading.value = true
  try {
    const [bomRes, indicatorsRes, collRes] = await Promise.all([
      metricsApi.getBomConfig(configId.value),
      metricsApi.listBomIndicators(configId.value),
      metricsApi.listAllCollections(),
    ])
    Object.assign(bom, bomRes.data)
    bom.version = bomRes.data.version || 1
    bomIndicators.value = indicatorsRes.data || []
    disconnectBomWebSocket()
    connectBomWebSocket()
    const collMap: Record<number, string> = {}
    for (const c of (collRes.data || [])) {
      collMap[c.id] = c.name
    }
    collectionName.value = collMap[bom.collection_id] || ''

     if (bom.collection_id) {
       // 使用新的批量接口一次性获取完整指标树，消除 N+1
       const fullRes = await metricsApi.getFullIndicatorsByConfig(configId.value)
       const fullItems = fullRes?.data || []
       
       testItems.value = fullItems.map((item: any) => {
         // 为每个指标构建 _param_map 供表格单元格编辑使用
         const indicatorList = item.indicators.map((ind: any) => {
           const sourceParams = ind.has_override ? (ind.params || []) : (ind.dict_params || [])
           const paramMap: Record<string, any> = {}
           for (const p of sourceParams) {
             const key = p.param_key || p.key
             if (!key) continue
             paramMap[key] = {
               value: p.param_value ?? p.value ?? '',
               remark: p.remark ?? '',
               format: p.format ?? p.type ?? 'string',
               name: p.param_name || p.name || key,
               required: p.required ?? false,
             }
           }
           return {
             ...ind,
             _bom_indicator_id: ind._bom_indicator_id || 0,
             indicator_code: ind.indicator_code || '',
             indicator_name: ind.indicator_name || '',
             category: ind.category || '',
             unit: ind.unit || '',
             _param_map: paramMap,
             _item: { id: item.test_item_id, name: item.test_item_name }
           }
         })
         return {
           ...item,
           indicatorList,
           _param_cols: indicatorList.length ? Object.keys(indicatorList[0]._param_map || {}) : [],
         }
       })
       
       domainOptions.value = ['全部领域', ...extractDomains(testItems.value)]
       if (domainFilter.value !== '全部领域' && !domainOptions.value.includes(domainFilter.value)) {
         domainFilter.value = '全部领域'
       }
       restoreDraft()
       if (!hasAutoExpanded.value) {
         autoExpandFirstEmptyStation()
         hasAutoExpanded.value = true
       }
     }
   } catch (e: any) {
     ElMessage.error('加载数据失败: ' + (e?.response?.data?.message || e.message || ''))
   } finally {
     loading.value = false
   }
 }

function mergeOverrides(itemIndicators: any[], bomIndicators: any[]): { indicatorList: any[], paramCols: { key: string, label: string, remark: string, format: string, required: boolean, minWidth?: number }[] } {
  const bomMap: Record<number, any> = {}
  for (const bi of bomIndicators) {
    bomMap[bi.indicator_id] = bi
  }
  const allParamCols: Record<string, { label: string, remark: string, format: string, required: boolean }> = {}
  const indicatorList = itemIndicators.map(ind => {
    const bomInd = bomMap[ind.indicator_id]
    const dictParams: any[] = ind.test_params || []
    const bomParams: any[] = bomInd?.params || []
    const hasOverride = bomParams.length > 0
    const sourceParams = hasOverride ? bomParams : dictParams
    const paramMap: Record<string, any> = {}
    for (const p of sourceParams) {
      const key = p.key || p.param_key
      if (!key) continue
      paramMap[key] = {
        value: p.param_value ?? p.value ?? '',
        remark: p.remark ?? '',
        format: p.format ?? p.type ?? 'string',
        name: p.param_name || p.name || key,
        required: p.required ?? false,
      }
      allParamCols[key] = {
        label: p.param_name || p.name || key,
        remark: p.remark ?? '',
        format: p.format ?? p.type ?? 'string',
        required: p.required ?? false,
      }
    }
    return {
      ...ind,
      _bom_indicator_id: bomInd?.id || 0,
      indicator_code: bomInd?.indicator_code || ind.indicator_code || ind.code || '',
      indicator_name: bomInd?.indicator_name || ind.indicator_name || ind.name || '',
      category: bomInd?.category || ind.category || '',
      unit: bomInd?.unit || ind.unit || '',
      process_name: bomInd?.process_name || '',
      station_name: bomInd?.station_name || '',
      _param_map: paramMap,
    }
  })
  const paramCols = Object.entries(allParamCols).map(([key, info]) => ({ key, ...info, minWidth: 140 }))
  return { indicatorList, paramCols }
}

// 保存成功后同步本地的 item_revision（后端每次原子递增 +1），
// 避免同一测试项连续编辑多处时因本地版本过期触发误报冲突。
function bumpLocalRevision(ind: any) {
  if (ind?._item?.item_revision != null) {
    ind._item.item_revision = Number(ind._item.item_revision) + 1
  }
}

// ── Inline Threshold Editing ──
function startEdit(row: any, field: string) {
  editRowId.value = row._bom_indicator_id || 0
  editField.value = field
}

async function saveThreshold(ind: any) {
  if (ind._item && !canEditItem(ind._item)) {
    ElMessage.warning('该测试项无编辑权限')
    return
  }
  const field = editField.value
  editRowId.value = 0
  editField.value = ''
  const item = ind._item
  const doSave = async () => {
    try {
      let bomIndicatorId = ind._bom_indicator_id
      if (!bomIndicatorId) {
        const createRes = await metricsApi.addBomIndicator(configId.value, {
          indicator_id: ind.indicator_id,
          unit: ind.unit || '',
          judgment_rule: '合格',
          test_stage: '',
          remark: '',
        })
        ind._bom_indicator_id = createRes.data?.id
        ind._bom_override = true
        await loadAll()
      } else {
        await metricsApi.updateBomIndicator(bomIndicatorId, {
          [field]: ind[field],
          test_item_id: item?.id ?? ind._item?.id,
          item_revision: item?.item_revision ?? ind._item?.item_revision ?? null,
        })
        bumpLocalRevision(ind)
      }
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.message || '保存失败')
      await loadAll()
    }
  }
  return enqueueItemSave(item?.id ?? ind._item?.id ?? 0, doSave)
}

// ── Inline param editing (flat columns) ──
async function saveParamValue(ind: any, paramKey: string) {
  if (ind._item && !canEditItem(ind._item)) {
    ElMessage.warning('该测试项无编辑权限')
    return
  }
  editParamKey.value = ''
  const info = ind._param_map?.[paramKey]
  const newValue = info?.value ?? info ?? ''
  const item = ind._item
  const doSave = async () => {
    try {
      let bomIndicatorId = ind._bom_indicator_id
      if (!bomIndicatorId) {
        const pmap: Record<string, any> = ind._param_map || {}
        const params = Object.entries(pmap).map(([k, v]) => ({
          param_key: k, param_name: v.name ?? k, param_value: v.value ?? v, format: v.format ?? 'string', remark: v.remark ?? '',
        }))
        const createRes = await metricsApi.addBomIndicator(configId.value, {
          indicator_id: ind.indicator_id,
          unit: ind.unit || '',
          params,
        })
        bomIndicatorId = createRes.data?.id
        ind._bom_indicator_id = bomIndicatorId
      }
      await metricsApi.updateBomIndicatorParam(bomIndicatorId, paramKey, {
        param_value: newValue,
        test_item_id: item?.id ?? ind._item?.id,
        item_revision: item?.item_revision ?? ind._item?.item_revision ?? null,
      })
      bumpLocalRevision(ind)
      saveDraft()
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.message || '保存失败')
      await loadAll()
    }
  }
  return enqueueItemSave(item?.id ?? ind._item?.id ?? 0, doSave)
}

function validateParamValue(paramKey: string, value: string, format: string): { valid: boolean; message: string } {
  const numericFormats = ['number', 'range', 'percent']
  const booleanFormats = ['boolean']
  const listFormats = ['array', 'list']
  const stringFormats = ['string', 'text', 'enum', 'expr']

  if (numericFormats.includes(format)) {
    if (value === '' || value === null || value === undefined) return { valid: true, message: '' }
    if (!/^[-+]?\d*\.?\d+$/.test(String(value))) {
      return { valid: false, message: '数字/范围/百分比参数仅允许整数或小数' }
    }
  } else if (booleanFormats.includes(format)) {
    if (value !== 'true' && value !== 'false') {
      return { valid: false, message: '布尔参数仅支持 true 或 false' }
    }
  } else if (listFormats.includes(format)) {
    if (value && value.includes('，')) {
      return { valid: false, message: '列表参数使用英文逗号分隔' }
    }
  }
  return { valid: true, message: '' }
}

async function validateAndSaveParam(ind: any, paramKey: string) {
  const info = ind._param_map?.[paramKey]
  if (!info) return
  const format = info.format || 'string'
  const value = info.value ?? ''
  const validation = validateParamValue(paramKey, String(value), format)
  if (!validation.valid) {
    ElMessage.warning(validation.message)
    return
  }
  await saveParamValue(ind, paramKey)
}

// ── Version Diff (published/archived versions only, test-item + param level) ──
async function loadArchivedSnapshots() {
  try {
    const res = await metricsApi.listVersions({ entity_type: 'bom', page_size: 200 })
    const all = res.data?.items || []
    // Only published/archived versions (评审通过/归档), hide intermediate process nodes
    archivedSnapshots.value = all.filter((v: any) => v.change_summary && (v.change_summary.includes('归档') || v.change_summary.includes('评审通过')))
  } catch {
    ElMessage.error('获取归档版本列表失败')
    archivedSnapshots.value = []
  }
}

async function loadPublishedVersions(bomId: number) {
  try {
    const verRes = await metricsApi.listVersions({
      entity_type: 'bom', entity_id: bomId, page_size: 100,
    })
    const allVersions = verRes.data?.items || []
    // Only published/archived versions (评审通过/归档); one version = one published storage
    diffDialog.publishedVersions = dedupVersions(allVersions.filter((v: any) => v.change_summary && (v.change_summary.includes('归档') || v.change_summary.includes('评审通过'))))
  } catch {
    ElMessage.error('获取版本列表失败')
    diffDialog.publishedVersions = []
  }
}

function clearDiffResult() {
  diffDialog.added = { newItems: [], newParams: [] }
  diffDialog.removed = { deletedItems: [], deletedParams: [] }
  diffDialog.modified = []
}

function queryBomSuggestions(query: string, cb: any) {
  const q = (query || '').toLowerCase().trim()
  const byCode: Record<string, number[]> = {}
  for (const s of archivedSnapshots.value) {
    const code = (s.snapshot_data?.bom_config?.bom_code || '') as string
    if (!code) continue
    if (q && !code.toLowerCase().includes(q)) continue
    if (!byCode[code]) byCode[code] = []
    if (!byCode[code].includes(s.version)) byCode[code].push(s.version)
  }
  const suggestions = Object.entries(byCode)
    .map(([code, versions]) => ({
      value: code,
      bom_code: code,
      versions: versions.sort((a, b) => b - a).map(v => `v${v}`).join('、'),
    }))
    .slice(0, 20)
  cb(suggestions)
}

async function onDiffBomSelected(item: any) {
  diffDialog.bomCode = item.bom_code
  diffDialog.selectedSnapshotId = 0
  diffDialog.showAllVersions = false
  diffDialog.publishedVersions = bomCodeSnapshots.value
  if (diffDialog.publishedVersions.length) {
    diffDialog.selectedSnapshotId = diffDialog.publishedVersions[0].id
    await loadArchivedDiff()
  } else {
    ElMessage.info('该 BOM 编码暂无已发布版本，无法对比')
    clearDiffResult()
  }
}

function onVersionChange(val: any) {
  if (val === '__more__') {
    diffDialog.showAllVersions = true
    diffDialog.selectedSnapshotId = diffDialog.publishedVersions[0]?.id
    return
  }
  if (val === '__less__') {
    diffDialog.showAllVersions = false
    diffDialog.selectedSnapshotId = diffDialog.publishedVersions[0]?.id
    return
  }
  if (val) loadArchivedDiff()
}

async function openVersionDiff() {
  diffDialog.loading = true
  diffDialog.visible = true
  try {
    await loadBaselineParams()
    await loadArchivedSnapshots()
    diffDialog.bomCode = bom.bom_code || ''
    diffDialog.showAllVersions = false
    diffDialog.selectedSnapshotId = 0
    diffDialog.publishedVersions = bomCodeSnapshots.value
    if (diffDialog.publishedVersions.length) {
      diffDialog.selectedSnapshotId = diffDialog.publishedVersions[0].id
      await loadArchivedDiff()
    } else {
      ElMessage.info('当前 BOM 编码暂无已发布版本可供对比')
      clearDiffResult()
    }
  } catch {
    ElMessage.error('获取版本对比失败')
  } finally {
    diffDialog.loading = false
  }
}

async function loadArchivedDiff() {
  if (!diffDialog.selectedSnapshotId) return
  diffDialog.loading = true
  try {
    // Refresh current BOM indicators so live diff reflects in-session edits
    const liveRes = await metricsApi.listBomIndicators(configId.value)
    bomIndicators.value = liveRes.data || []
    const snapshotRes = await metricsApi.getVersionDetail(diffDialog.selectedSnapshotId)
    const snapshot = snapshotRes.data?.snapshot_data
    if (!snapshot) { ElMessage.info('所选版本数据不可用'); return }

    const currentIndicators = buildLiveIndicatorMap()
    const archivedIndicators = buildArchivedIndicatorMap(snapshot)

    const added = { newItems: [] as any[], newParams: [] as any[] }
    const removed = { deletedItems: [] as any[], deletedParams: [] as any[] }
    const modified: any[] = []

    const allIndicators = new Set<number>([...Object.keys(currentIndicators).map(Number), ...Object.keys(archivedIndicators).map(Number)])
    const pn = (ind: any) => ind.process_name || ''
    const sn = (ind: any) => ind.station_name || ''
    for (const indId of allIndicators) {
      const cur = currentIndicators[indId]
      const arc = archivedIndicators[indId]
      const procName = pn(cur || arc)
      const staName = sn(cur || arc)
      if (cur && !arc) {
        added.newItems.push(cur)
      } else if (arc && !cur) {
        removed.deletedItems.push(arc)
      } else if (cur && arc) {
        const paramDiff = compareParams(cur, arc)
        if (paramDiff.added.length) {
          for (const p of paramDiff.added) {
            added.newParams.push({ indicatorName: cur.name || cur.code, process_name: procName, station_name: staName, paramName: p.key, newValue: p.value })
          }
        }
        if (paramDiff.removed.length) {
          for (const p of paramDiff.removed) {
            removed.deletedParams.push({ indicatorName: arc.name || arc.code, process_name: procName, station_name: staName, paramName: p.key, oldValue: p.value })
          }
        }
        for (const pm of paramDiff.modified) {
          modified.push({
            indicatorName: cur.name || cur.code,
            process_name: procName,
            station_name: staName,
            paramName: pm.name || pm.key,
            oldValue: pm.before,
            newValue: pm.after,
            diffLabel: pm.fieldLabel || '',
          })
        }
      }
    }

    diffDialog.added = added
    diffDialog.removed = removed
    diffDialog.modified = modified
  } catch {
    ElMessage.error('获取版本对比失败')
  } finally {
    diffDialog.loading = false
  }
}

function diffSpanMethodHelper(rows: any[], { row, _column, rowIndex, columnIndex }: any): any {
  if (columnIndex !== 0) return
  if (rowIndex > 0 && rows[rowIndex - 1]?.indicatorName === row.indicatorName) {
    return { rowspan: 0, colspan: 0 }
  }
  let rowspan = 1
  for (let i = rowIndex + 1; i < rows.length; i++) {
    if (rows[i].indicatorName === row.indicatorName) rowspan++
    else break
  }
  return { rowspan, colspan: 1 }
}
function diffSpanMethod(args: any) { return diffSpanMethodHelper(diffDialog.modified, args) }
function diffSpanMethodAdded(args: any) { return diffSpanMethodHelper(diffDialog.added.newParams, args) }
function diffSpanMethodRemoved(args: any) { return diffSpanMethodHelper(diffDialog.removed.deletedParams, args) }

function buildLiveIndicatorMap(): Record<number, any> {
  const map: Record<number, any> = {}
  for (const ind of bomIndicators.value) {
    const bomParams = ind.params || []
    const dictParams = ind.dict_params || []
    // Mirror archived map: BOM overrides win, else fall back to dict params
    const sourceParams = bomParams.length > 0 ? bomParams : dictParams
    const paramList = sourceParams.map((p: any) => ({
      key: p.key || p.param_key,
      value: p.param_value ?? p.value ?? '',
      name: p.param_name || p.name || p.key || '',
    }))
    map[ind.indicator_id] = {
      indicator_id: ind.indicator_id,
      code: ind.indicator_code || ind.code || '',
      name: ind.indicator_name || ind.name || '',
      unit: ind.unit || '',
      process_name: ind.process_name || '',
      station_name: ind.station_name || '',
      params: paramList,
    }
  }
  return map
}

function buildArchivedIndicatorMap(snapshot: any): Record<number, any> {
  const map: Record<number, any> = {}
  const indicators = snapshot?.indicators || []
  for (const ind of indicators) {
    const bomParams = ind.params || []
    const dictParams = ind.dict_params || []
    // Mirror live mergeOverrides: if BOM overrides exist use them, else fall back to dict params
    const sourceParams = bomParams.length > 0 ? bomParams : dictParams
    const paramList = sourceParams.map((p: any) => ({
      key: p.key || p.param_key,
      value: p.param_value ?? p.value ?? '',
      name: p.param_name || p.name || p.key || '',
    }))
    map[ind.indicator_id] = {
      indicator_id: ind.indicator_id,
      code: ind.code || '',
      name: ind.name || ind.indicator_name || '',
      unit: ind.unit || '',
      process_name: ind.process_name || '',
      station_name: ind.station_name || '',
      params: paramList,
    }
  }
  return map
}

function compareParams(cur: any, arc: any): { added: any[], removed: any[], modified: any[] } {
  const curMap: Record<string, any> = {}
  for (const p of (cur.params || [])) { curMap[p.key] = p }
  const arcMap: Record<string, any> = {}
  for (const p of (arc.params || [])) { arcMap[p.key] = p }
  const added: any[] = []
  const removed: any[] = []
  const modified: any[] = []
  const allKeys = new Set([...Object.keys(curMap), ...Object.keys(arcMap)])
  for (const k of allKeys) {
    const c = curMap[k]
    const a = arcMap[k]
    if (c && !a) added.push({ key: k, value: c.value })
    else if (a && !c) removed.push({ key: k, value: a.value })
    else if (c && a && String(c.value) !== String(a.value)) {
      modified.push({ key: k, name: c.name || a.name || k, before: a.value, after: c.value, fieldLabel: '参数值' })
    }
  }
  return { added, removed, modified }
}

function diffFieldLabel(field: string): string {
  const map: Record<string, string> = {
    upper_limit: '上限', lower_limit: '下限', unit: '单位',
    judgment_rule: '判定规则', test_stage: '测试阶段', remark: '备注', params: '硬件参数',
  }
  return map[field] || field
}

// ── Right Toolbar State ──
const rightToolbar = reactive({
  visible: true,
  batchCopyMode: 'single',
  selectedItems: [] as any[],
  copySourceItems: [] as any[],
  batchFillThreshold: { upper: '', lower: '' },
  exportProcessName: '' as string,
  exportStationName: '' as string,
  exportDimension: 'bom' as string,
})


function batchFillThreshold() {
  const { upper, lower } = rightToolbar.batchFillThreshold
  if (!upper && !lower) { ElMessage.warning('请输入上限或下限值'); return }
  for (const item of rightToolbar.selectedItems.length ? rightToolbar.selectedItems : testItems.value.flatMap((ti: any) => ti.indicatorList || [])) {
    const params = item._param_map || {}
    for (const key of Object.keys(params)) {
      const format = params[key].format || ''
      if (['number', 'range', 'percent'].includes(format)) {
        if (upper) params[key].value = upper
        if (lower) params[key].value = lower
      }
    }
  }
  saveAllPendingParams()
  ElMessage.success('批量填充完成')
}

// ── Export ──
function handleExport() {
  exportDialog.format = 'json'
  exportDialog.visible = true
}

async function submitExport() {
  exporting.value = true
  try {
    const res = await metricsApi.exportBomConfig(configId.value, { output_format: exportDialog.format })
    const data = res.data
    if (data?.download_url) {
      window.open(data.download_url, '_blank')
    }
    ElMessage.success(`导出成功（${data?.execution_time_ms || 0}ms）`)
    exportDialog.visible = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || e?.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

async function handleExportAction(cmd: string) {
  try {
    let res: any
    if (cmd === 'config') {
      exportDialog.visible = true
      return
    } else if (cmd === 'excel') {
      res = await metricsApi.exportBomExcel(configId.value)
    } else if (cmd === 'diff-report') {
      res = await metricsApi.exportBomDiffReport(configId.value)
    }
    const data = res?.data
    if (data?.download_url) {
      window.open(data.download_url, '_blank')
    }
    ElMessage.success('导出成功')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || e?.message || '导出失败')
  }
}

// ── Excel Template Import / Export ──
async function exportDiffReport() {
  try {
    if (!diffDialog.modified.length && !diffDialog.added.newParams.length && !diffDialog.removed.deletedParams.length) {
      await loadPublishedVersions(configId.value)
      if (diffDialog.publishedVersions.length) {
        diffDialog.selectedSnapshotId = diffDialog.publishedVersions[0].id
        await loadArchivedDiff()
      }
    }
    if (!diffDialog.modified.length && !diffDialog.added.newParams.length && !diffDialog.removed.deletedParams.length) {
      ElMessage.info('当前无差异数据可导出')
      return
    }
    ElMessage.info('正在导出差异报告...')
    const res = await metricsApi.exportDiffReport(configId.value, {})
    const data = res.data
    if (data?.download_url) {
      window.open(data.download_url, '_blank')
      ElMessage.success('差异报告导出成功')
    } else {
      ElMessage.error('导出失败: 服务器未返回下载链接')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || e?.message || '导出失败')
  }
}

async function exportPdfReport() {
  try {
    ElMessage.info('正在生成 PDF 评审配置单...')
    const res = await metricsApi.exportPdfReport(configId.value)
    const data = res.data
    if (data?.download_url) {
      window.open(data.download_url, '_blank')
      ElMessage.success('PDF 评审配置单导出成功')
    } else {
      ElMessage.error('导出失败: 服务器未返回下载链接')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || e?.message || '导出失败')
  }
}

async function exportExcelTemplate() {
  try {
    ElMessage.info('正在导出空白模板...')
    const res = await metricsApi.exportBomTemplate(configId.value)
    const data = res.data
    if (data?.download_url) {
      window.open(data.download_url, '_blank')
      ElMessage.success('导出成功')
    } else {
      ElMessage.error('导出失败: 服务器未返回下载链接')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || e?.message || '导出失败')
  }
}

async function exportCurrentConfig() {
  try {
    let procName = rightToolbar.exportProcessName || ''
    let staName = rightToolbar.exportStationName || ''
    const dim = rightToolbar.exportDimension || 'bom'
    if (!procName && !staName && dim !== 'bom') {
      if (dim === 'process' && expandedProcesses.value.length) {
        procName = expandedProcesses.value[0]
      } else if (dim === 'station' && expandedStations.value.length) {
        const [pn, sn] = expandedStations.value[0].split('::')
        procName = pn; staName = sn
      }
    }
    const label = staName ? `工位「${staName}」` : procName ? `工序「${procName}」` : '全 BOM'
    ElMessage.info(`正在导出${label}配置...`)
    const res = await metricsApi.exportCurrentConfig(configId.value, {
      process_name: procName || undefined,
      station_name: staName || undefined,
    })
    rightToolbar.exportProcessName = ''
    rightToolbar.exportStationName = ''
    const data = res.data
    if (data?.download_url) {
      window.open(data.download_url, '_blank')
      ElMessage.success(`导出${label}成功`)
    } else {
      ElMessage.error('导出失败: 服务器未返回下载链接')
    }
  } catch (e: any) {
    rightToolbar.exportProcessName = ''
    rightToolbar.exportStationName = ''
    ElMessage.error(e?.response?.data?.message || e?.message || '导出失败')
  }
}

async function openImport() {
  importDialog.visible = true
  importResult.value = null
}

async function importExcel() {
  try {
    await ElMessageBox.confirm('确认导入Excel文件？导入操作将更新所有指标的参数值，上限/下限和单位；此操作不可撤销！', '确认导入Excel', {
      type: 'warning',
      confirmButtonText: '确认导入',
      cancelButtonText: '取消'
    })
    
    const fileInput = document.createElement('input')
    fileInput.type = 'file'
    fileInput.accept = '.xlsx, .xls'
    fileInput.multiple = false
    
    fileInput.onchange = async (e: Event) => {
      const target = e.target as HTMLInputElement
      if (!target.files?.length) return
      
      const file = target.files[0]
      if (!file) return
      
      if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        ElMessage.error('请上传 .xlsx 或 .xls 文件')
        return
      }
      
      importDialog.loading = true
      try {
        const formData = new FormData()
        formData.append('file', file)
        
        const res = await metricsApi.importBomConfig(configId.value, formData)
        importResult.value = res.data
        
        ElMessage.success('Excel导入完成')
        await loadAll()
        clearDraft()
      } catch (e: any) {
        ElMessage.error(e?.response?.data?.message || e?.message || '导入失败')
      } finally {
        importDialog.loading = false
        fileInput.value = ''
      }
    }
    
    fileInput.click()
    
  } catch { /* cancelled */ }
}

// ── Review / Archive ──
// ── Save all pending params to backend (optimistic-lock batch save) ──
function nonEditableDirtyCount(): number {
  let n = 0
  for (const item of testItems.value) {
    if (canEditItem(item)) continue
    for (const ind of item.indicatorList || []) {
      const map = ind._param_map || {}
      for (const key of Object.keys(map)) {
        if (isParamDirty(ind.indicator_id, key)) { n++; break }
      }
    }
  }
  return n
}

async function saveAllPendingParams() {
  editParamKey.value = ''
  // 统计无权限测试项中是否有本地待保存的修改（提交时后端会丢弃这些变更）
  const droppedCount = nonEditableDirtyCount()
  // First pass: ensure every indicator has a BOM indicator record
  for (const item of testItems.value) {
    if (!canEditItem(item)) continue
    for (const ind of item.indicatorList || []) {
      const map = ind._param_map || {}
      if (!Object.keys(map).length) continue
      if (ind._bom_indicator_id) continue
       const params = Object.entries(map).map(([k, v]: [string, any]) => ({
         param_key: k, param_name: v.name ?? k, param_value: v.value ?? v, format: v.format ?? 'string', remark: v.remark ?? '',
       }))
       const createRes = await metricsApi.addBomIndicator(configId.value, {
         indicator_id: ind.indicator_id,
         unit: ind.unit || '',
         params,
       })
       ind._bom_indicator_id = createRes.data?.id
    }
  }
  // Second pass: collect all param values grouped by test item, then batch-save
  const payload: any[] = []
  for (const item of testItems.value) {
    if (!canEditItem(item)) continue
    for (const ind of item.indicatorList || []) {
      const id = ind._bom_indicator_id
       if (!id) continue
       const map = ind._param_map || {}
       for (const key of Object.keys(map)) {
        payload.push({
          indicator_id: id,
          param_key: key,
          param_value: String(map[key].value ?? ''),
          item_revision: item.item_revision ?? 0,
          test_item_id: item.id,
          test_item_name: item.name || '',
        })
       }
     }
   }
  if (droppedCount > 0) {
    ElMessage.warning(`部分测试项不属于你负责，修改无法保存（${droppedCount} 项被跳过）`)
  }
  if (!payload.length) return true
  try {
    const res = await metricsApi.batchSaveIndicatorParams(configId.value, { indicators: payload })
    const conflicts = res.data?.conflicts || []
    if (conflicts.length) {
      showSaveConflicts(conflicts)
      await loadAll()
      return false
    }
    // 保存成功：同步本地各测试项版本号（每个成功组 +1），后续再次保存不会误报冲突
    const savedItemIds = new Set<number>()
    for (const p of payload) {
      if (p.test_item_id) savedItemIds.add(Number(p.test_item_id))
    }
    for (const item of testItems.value) {
      if (savedItemIds.has(Number(item.id))) {
        item.item_revision = (Number(item.item_revision ?? 0) || 0) + 1
      }
    }
    return true
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '批量保存失败')
    await loadAll()
    return false
  }
}

const conflictDialog = reactive({ visible: false, conflicts: [] as any[] })

function showSaveConflicts(conflicts: any[]) {
  conflictDialog.conflicts = conflicts
  conflictDialog.visible = true
}

// ── 参数变更记录对话框 ──
const changeLogDialog = reactive({ visible: false, loading: false, itemName: '', logs: [] as any[] })

async function openChangeLogDialog(item: any) {
  changeLogDialog.itemName = item.name || ''
  changeLogDialog.visible = true
  changeLogDialog.loading = true
  changeLogDialog.logs = []
  try {
    const res = await metricsApi.getChangeLogs(configId.value, { test_item_id: item.id })
    changeLogDialog.logs = res.data || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '加载变更记录失败')
  } finally {
    changeLogDialog.loading = false
  }
}

async function handleSubmitReview() {
  try {
    await ElMessageBox.confirm('确认提交评审？提交前将进行必填参数校验。', '提交评审')
    await validateAndSave()
    const ok = await saveAllPendingParams()
    if (!ok) return
    await metricsApi.submitReview(configId.value, { comment: '' })
    clearDraft()
    ElMessage.success('已提交评审')
    await loadAll()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.message || e?.message || '提交评审失败')
  }
}

async function handleWithdrawReview() {
  try {
    await ElMessageBox.confirm('确认撤回评审？撤回后参数编辑权限将恢复。', '撤回评审')
    await metricsApi.withdrawReview(configId.value)
    clearDraft()
    ElMessage.success('评审已撤回')
    await loadAll()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.message || e?.message || '撤回评审失败')
  }
}

async function handleApproveReview() {
  try {
    const { value } = await ElMessageBox.prompt('评审意见（可选）', '评审通过', { inputType: 'textarea' })
    await metricsApi.approveReview(configId.value, { comment: value || '' })
    clearDraft()
    ElMessage.success('评审已通过')
    await loadAll()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.message || e?.message || '评审通过失败')
  }
}

async function handleRejectReview() {
  try {
    const { value } = await ElMessageBox.prompt('驳回原因（必填）', '驳回', {
      inputType: 'textarea', inputValidator: (v: string) => !!v || '请填写驳回原因',
    })
    await metricsApi.rejectReview(configId.value, { comment: value || '' })
    ElMessage.success('评审已驳回')
    await loadAll()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.message || e?.message || '驳回失败')
  }
}

async function handleArchive() {
  try {
    await ElMessageBox.confirm('确认归档？归档后该版本将被锁定，不可再编辑。', '归档', { type: 'warning', confirmButtonText: '确认归档' })
    await metricsApi.archiveBom(configId.value)
    clearDraft()
    ElMessage.success('BOM 已归档')
    await loadAll()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.message || e?.message || '归档失败')
  }
}

async function handleResetDraft() {
  try {
    await ElMessageBox.confirm(
      '此操作将所有参数值恢复为归档基准原值，覆盖当前编辑中的值。该操作不可撤销，确认继续？',
      '高危操作确认：重置编辑',
      { type: 'warning', confirmButtonText: '确认重置', cancelButtonText: '取消' },
    )
    clearDraft()
    let copied = 0
    for (const proc of processTreeData.value) {
      for (const sta of proc.stations) {
        for (const item of sta.items) {
          for (const row of getItemParamRows(item)) {
            const bv = baselineParams.value[row._ind.indicator_id + '#' + row.param_key]
            if (bv !== undefined) {
              row._ind._param_map[row.param_key].value = bv
              copied++
            }
          }
        }
      }
    }
    saveDraft()
    const ok = await saveAllPendingParams()
    if (ok) {
      ElMessage.success(`已重置为归档基准原值，共恢复 ${copied} 个参数`)
    } else {
      ElMessage.warning('已重置为归档基准原值，但保存时存在冲突，请处理后再试')
    }
  } catch { /* cancelled */ }
}

// ── Pre-save Validation ──
async function validateAndSave() {
  validationDialog.visible = true
  validationDialog.loading = true
  validationError.value = ''
  try {
    const res = await metricsApi.validateBomConfig(configId.value)
    const payload = res.data?.data || res.data
    validationResult.value = payload
    validationErrors.value = payload?.errors || []
    if (validationErrors.value.length > 0) {
      ElMessage.error(`存在 ${validationErrors.value.length} 个参数未填写`)
      scrollToFirstError()
    } else {
      ElMessage.success('校验通过')
    }
  } catch (e: any) {
    const msg = e?.response?.data?.message || e?.response?.data?.detail || e?.message || '校验失败'
    validationError.value = msg
    validationErrors.value = []
    ElMessage.error(msg)
  } finally {
    validationDialog.loading = false
  }
}

function scrollToFirstError() {
  if (!validationErrors.value.length) return
  const firstError = validationErrors.value[0]
  if (firstError?.indicator_id && firstError?.param_key) {
    const el = document.getElementById(`item-${firstError.indicator_id}`)
    if (el) {
      const procEl = el.closest('[data-process]')
      if (procEl) {
        const procName = procEl.getAttribute('data-process')
        if (procName && !expandedProcesses.value.includes(procName)) {
          expandedProcesses.value.push(procName)
        }
      }
      const staEl = el.closest('[data-station]')
      if (staEl && procEl) {
        const staName = staEl.getAttribute('data-station')
        const pn = procEl.getAttribute('data-process') || ''
        if (staName && !isStationExpanded(pn, staName)) toggleStationExpand(pn, staName)
      }
      scrollItemIntoView(firstError.indicator_id)
    }
  }
}

function scrollToError(error: any) {
  if (!error?.indicator_id && !error?.indicator_name) return
  validationDialog.visible = false
  // Find indicator in current items
  for (const item of testItems.value) {
    const found = (item.indicatorList || []).find((ind: any) => 
      ind.indicator_id === error.indicator_id || ind.indicator_name === error.indicator_name
    )
    if (found) {
      const el = document.getElementById(`item-${item.id}`)
      if (el) {
        const procEl = el.closest('[data-process]')
        if (procEl) {
          const procName = procEl.getAttribute('data-process')
          if (procName && !expandedProcesses.value.includes(procName)) {
            expandedProcesses.value.push(procName)
          }
        }
        const staEl = el.closest('[data-station]')
        if (staEl && procEl) {
          const staName = staEl.getAttribute('data-station')
          const pn = procEl.getAttribute('data-process') || ''
          if (staName && !isStationExpanded(pn, staName)) toggleStationExpand(pn, staName)
        }
        scrollItemIntoView(item.id)
      }
      break
    }
  }
}

// ── Auto-save draft before page unload (works for both SPA nav + refresh) ──
function onPageBeforeUnload() {
  saveDraft()
}
window.addEventListener('beforeunload', onPageBeforeUnload)

// ── Global shortcuts: Ctrl+S / Cmd+S save all ──
async function onGlobalKeydown(e: KeyboardEvent) {
  handleNavKeydown(e)
  if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
    e.preventDefault()
    if (bom.archived || bom.review_status === 'pending') return
    try {
      const ok = await saveAllPendingParams()
      if (ok) ElMessage.success('已保存全部参数')
    } catch (err: any) {
      ElMessage.error(err?.response?.data?.message || '保存失败')
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', onGlobalKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onPageBeforeUnload)
  window.removeEventListener('keydown', onGlobalKeydown)
  saveDraft()
  disconnectBomWebSocket()
})

async function handleNewIteration() {
  try {
    let hasNonClosed = false
    try {
      const checkRes = await metricsApi.checkBomVersion(bom.bom_code, configId.value)
      hasNonClosed = checkRes.data?.has_non_closed || false
    } catch { /* pre-check unavailable, proceed anyway */ }
    if (hasNonClosed) {
      ElMessageBox.alert('该BOM编码已存在未评审/未归档版本，不允许新建迭代', '无法新建迭代', {
        confirmButtonText: '确定', type: 'warning',
      })
      return
    }
    const label = bom.archived ? '已归档' : '已发布'
    await ElMessageBox.confirm(`将基于当前${label}版本创建新迭代\n\nBOM编码: ${bom.bom_code}\n当前版本: v${bom.version}\n\n新版本将复制所有指标和参数数据，生成未评审的迭代版本继续编辑？`, '基于此版本新建')
    const res = await metricsApi.createNewIteration(configId.value)
    const newId = res.data?.id
    ElMessage.success(`新迭代版本 v${res.data?.version} 已创建`)
    if (newId) {
      const isCodePage = ['BomCodeEdit', 'BomCodeDomain'].includes(String(route.name))
      if (isCodePage) {
        router.replace({ name: 'BomCodeEdit', params: { bomCode: bom.bom_code, id: newId } })
      } else {
        router.push({ name: 'BomDetail', params: { id: newId } })
      }
    }
  } catch (e: any) {
    if (e?.response?.data?.message) {
      ElMessage.error(e.response.data.message)
    } else if (e?.message && e.message !== 'cancel' && e?.message !== '取消') {
      ElMessage.error(e.message)
    }
  }
}

// Auto-expand first station with empty params when data loads
onMounted(() => {
  loadAll()
  loadBaselineParams()
  loadUserOptions()
  restoreDomainFilter()
})

onBeforeRouteUpdate((to) => {
  disconnectBomWebSocket()
  configId.value = Number(to.params.id || 0)
  loadAll()
  loadBaselineParams()
})
</script>

<style>
.diff-added-row td { background-color: #f0f9eb !important; }
.diff-removed-row td { background-color: #fef0f0 !important; }
.diff-removed-row .cell { text-decoration: line-through; color: #f56c6c !important; }
.el-table .diff-added-row:hover td { background-color: #e6f7d4 !important; }
.el-table .diff-removed-row:hover td { background-color: #fde2e2 !important; }

.param-dirty .el-input__wrapper { box-shadow: 0 0 0 1px #f56c6c inset !important; }
.param-dirty .el-select .el-select__wrapper { box-shadow: 0 0 0 1px #f56c6c inset !important; }
.param-dirty .text-sm { color: #f56c6c !important; font-weight: 500; }
.param-dirty .text-sm.text-danger { color: #cc0000 !important; }

.validation-error-row td { background-color: #fef2f2 !important; }
.validation-error-header { background-color: #fef2f2 !important; }

/* Hover-only copy button in baseline column */
.copy-baseline-btn { visibility: hidden; }
.el-table__row:hover .copy-baseline-btn { visibility: visible; }

/* Compact density mode */
.compact-mode .mb-6 { margin-bottom: 0.375rem; }
.compact-mode .p-2 { padding: 0.25rem; }
.compact-mode .px-4 { padding-left: 0.5rem; padding-right: 0.5rem; }
.compact-mode .py-2 { padding-top: 0.25rem; padding-bottom: 0.25rem; }
.compact-mode .py-1.5 { padding-top: 0.25rem; padding-bottom: 0.25rem; }
.compact-mode .space-y-3 > * + * { margin-top: 0.375rem; }
.compact-mode .space-y-2 > * + * { margin-top: 0.25rem; }
.compact-mode .el-table td.el-table__cell { padding-top: 1px; padding-bottom: 1px; }
.compact-mode .el-table .cell { line-height: 1.35; }
.compact-mode .el-table__header th.el-table__cell { padding-top: 2px; padding-bottom: 2px; }
</style>
