<template>
  <div>
    <div class="flex items-center gap-2 mb-4">
      <el-icon :size="26" color="var(--el-color-primary)"><Box /></el-icon>
      <div>
        <h1 class="section-title !mb-0 !border-0 !pl-0 text-xl">版本管理</h1>
        <div class="section-subtitle mt-0.5">版本发布 · 发行部署 · 审批流转</div>
      </div>
    </div>

    <el-card class="app-card app-card-hover">
      <el-tabs v-model="activeTab">
        <!-- Tab1: Version List -->
        <el-tab-pane name="list">
          <template #label><el-icon class="mr-1 align-middle"><List /></el-icon>版本列表</template>
          <div class="mb-4">
            <el-radio-group v-model="listScope" @change="onScopeChange">
              <el-radio-button label="mine">我的版本</el-radio-button>
              <el-radio-button label="all">全部版本</el-radio-button>
            </el-radio-group>
          </div>

          <div class="table-toolbar">
            <el-form :inline="true" size="small">
              <el-form-item label="状态">
                <el-select v-model="listFilters.status" clearable placeholder="全部" style="width: 120px">
                  <el-option label="草稿" value="draft" />
                  <el-option label="已发布" value="released" />
                  <el-option label="已发行" value="deployed" />
                  <el-option label="已下架" value="delisted" />
                </el-select>
              </el-form-item>
              <el-form-item label="项目">
                <el-input v-model="listFilters.project_name" placeholder="项目名称" style="width: 140px" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="fetchVersions">
                  <el-icon class="mr-1"><Search /></el-icon>查询
                </el-button>
              </el-form-item>
            </el-form>
            <el-button type="primary" size="small" @click="startCreate">
              <el-icon class="mr-1"><Plus /></el-icon>创建版本
            </el-button>
          </div>

          <el-table :data="versions" v-loading="versionsLoading" stripe style="width: 100%" size="small">
            <template #empty>
              <div class="flex flex-col items-center py-8 text-gray-400">
                <el-icon :size="36" color="#c0c8d4"><FolderOpened /></el-icon>
                <div class="mt-2 text-sm">暂无版本数据</div>
                <div class="text-xs mt-1">点击右上角「创建版本」开始新建</div>
              </div>
            </template>
            <el-table-column prop="project_name" label="项目" width="120" show-overflow-tooltip align="center" header-align="center" />
            <el-table-column prop="version" label="版本号" width="100" align="center" header-align="center" />
            <el-table-column prop="type" label="类型" width="110" align="center" header-align="center">
              <template #default="{ row }">{{ typeLabel(row.type) }}</template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80" align="center" header-align="center">
              <template #default="{ row }">
                <el-tag :type="versionStatusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="bom_code" label="BOM编码" width="120" show-overflow-tooltip align="center" header-align="center" />
            <el-table-column prop="created_by" label="创建人" width="90" align="center" header-align="center" />
            <el-table-column prop="created_at" label="创建时间" width="160" align="center" header-align="center" />
            <el-table-column label="操作" width="360" fixed="right" align="center" header-align="center">
              <template #default="{ row }">
                <div class="flex items-center gap-1 whitespace-nowrap">
                  <el-button link size="small" @click="viewVersion(row)">
                    <el-icon class="mr-0.5"><View /></el-icon>详情
                  </el-button>
                  <el-button link size="small" v-if="row.status === 'draft'" @click="editVersion(row)">
                    <el-icon class="mr-0.5"><Edit /></el-icon>编辑
                  </el-button>
                  <el-button link size="small" v-if="row.status === 'delisted'" type="warning" @click="handleRestore(row)">
                    <el-icon class="mr-0.5"><RefreshLeft /></el-icon>恢复
                  </el-button>
                  <el-button link size="small" v-if="row.status === 'draft' || row.status === 'delisted'" type="danger" @click="handleDeleteVersion(row)">
                    <el-icon class="mr-0.5"><Delete /></el-icon>删除
                  </el-button>
                  <el-button link size="small" v-if="row.status === 'released'" type="success" @click="goDeployWith(row)">
                    <el-icon class="mr-0.5"><Promotion /></el-icon>发行
                  </el-button>
                  <el-button link size="small" v-if="row.status !== 'delisted'" type="info" @click="handleDelist(row)">
                    <el-icon class="mr-0.5"><Bottom /></el-icon>下架
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <div class="flex justify-end mt-3">
            <el-pagination
              v-model:current-page="versionPage"
              :page-size="versionPageSize"
              :total="versionTotal"
              layout="total, prev, pager, next"
              @current-change="fetchVersions"
            />
          </div>
        </el-tab-pane>

        <!-- Tab 2: Version Release (create + release workspace) -->
        <el-tab-pane name="release">
          <template #label><el-icon class="mr-1 align-middle"><Promotion /></el-icon>版本发布</template>
          <!-- CREATE MODE: build & publish the version -->
          <template v-if="releaseMode === 'create'">
            <div class="mb-3 text-sm text-gray-500">
              填写版本信息并配置子场景，保存后自动进入发布流程（测试经理 / 项目经理审批）。
            </div>
            <el-form :model="createForm" label-width="140px" v-loading="createLoading">
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="版本类型" required>
                    <el-select v-model="createForm.type" class="w-full" @change="onTypeChange">
                      <el-option label="标准" value="standard" />
                      <el-option label="多工序版本" value="multi_process" />
                      <el-option label="产品族版本" value="product_family" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="工程名称" required>
                    <el-autocomplete
                      v-model="createForm.project_name"
                      :fetch-suggestions="queryProjectNames"
                      placeholder="输入可联想已存在的工程名称"
                      clearable
                      class="w-full"
                      @select="onProjectNameBlur"
                      @blur="onProjectNameBlur"
                    />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="版本号" required>
                    <el-input v-model="createForm.version" placeholder="如 2.1.0" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="自动继承上一版本">
                    <el-switch
                      v-model="createForm.auto_inherit"
                      :active-value="true"
                      :inactive-value="false"
                      @change="onAutoInheritChange"
                    />
                    <span class="text-xs text-gray-400 ml-2">继承相同工程名称的上一版本配置</span>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="工序工位标签">
                <el-input v-model="createForm.domain_tags" placeholder="多个用逗号分隔，如 FT,MP1" />
              </el-form-item>
              <el-form-item label="版本描述">
                <el-input v-model="createForm.description" type="textarea" :rows="2" />
              </el-form-item>
              <el-row :gutter="20" v-if="createForm.type !== 'standard'">
                <el-col :span="12">
                  <el-form-item label="BOM 编码" required>
                    <el-input
                      v-model="createForm.bom_code"
                      placeholder="多个用逗号或分号分隔，如 BOM1,BOM2"
                    />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="TPS 名称" v-if="createForm.type === 'multi_process'">
                    <el-input v-model="createForm.tps_name" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="继承自">
                <el-select
                  v-model="createForm.inherit_from_id"
                  filterable clearable
                  class="w-full"
                  placeholder="仅可选同一工程的历史版本"
                  @change="onInheritChange"
                >
                  <el-option
                    v-for="v in existingVersions.filter(v => v.project_name === createForm.project_name)"
                    :key="v.id"
                    :label="`${v.version} — ${v.project_name}`"
                    :value="v.id"
                  />
                </el-select>
                <span class="text-xs text-gray-400 ml-2" v-if="createForm.project_name">
                  仅显示「{{ createForm.project_name }}」的历史版本
                </span>
              </el-form-item>

              <!-- ② 继承源完整配置预览（选中继承后展示，可直接编辑） -->
              <el-alert
                v-if="inheritSource"
                type="success"
                :closable="false"
                show-icon
                class="mb-3"
                :title="`已继承基版 #${inheritSource.id}（${inheritSource.version}）的全部配置，可直接修改、新增、删除`"
              >
                <template #default>
                  <div class="text-xs text-gray-600 mt-1">
                    <div>基础信息：类型 {{ typeLabel(inheritSource.type) }} ｜ BOM {{ inheritSource.bom_code || '-' }} ｜ TPS {{ inheritSource.tps_name || '-' }}</div>
                    <div v-if="inheritSource.sub_scenarios?.length">
                      子场景（{{ inheritSource.sub_scenarios.length }}）：
                      <span class="mr-2" v-for="ss in inheritSource.sub_scenarios" :key="ss.id">{{ ss.name }}</span>
                    </div>
                    <div>基版固件附件：{{ inheritSource.binary_files?.length || 0 }} 个（发布时同步复制到新版本）</div>
                  </div>
                </template>
              </el-alert>

              <el-divider>子场景</el-divider>
              <div class="mb-3" v-if="createForm.type !== 'standard'">
                <span class="text-xs text-gray-500 mr-2">快速添加内置类型：</span>
                <el-tag
                  v-for="p in subScenarioPresets"
                  :key="p"
                  class="cursor-pointer mr-2 mb-1"
                  effect="plain"
                  @click="addPresetScenario(p)"
                >+ {{ p }}</el-tag>
                <span class="text-xs text-gray-400 ml-1">（格式：工序-工位，如 FT-MP9，自动转大写）</span>
              </div>
              <div v-for="(ss, i) in createForm.sub_scenarios" :key="i" class="border rounded p-3 mb-3">
                <el-row :gutter="12">
                  <el-col :span="8">
                    <el-form-item :label="`场景 ${i+1}`" :prop="`sub_scenarios.${i}.name`" required>
                      <el-input
                        :model-value="ss.name"
                        @update:model-value="(v: any) => ss.name = (v || '').toUpperCase()"
                        placeholder="工序-工位，如 FT-MP1"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item label="工序">
                      <el-input v-model="ss.process_type" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item label="工位">
                      <el-input v-model="ss.workstation" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="4" class="flex items-end">
                    <el-button type="danger" size="small" @click="createForm.sub_scenarios.splice(i, 1)">移除</el-button>
                  </el-col>
                </el-row>
                 <el-form-item label="测试序列">
                   <el-select v-model="ss.sequence_id" filterable clearable class="w-full">
                     <el-option v-for="s in sequences" :key="s.id" :label="s.name" :value="s.id" />
                   </el-select>
                 </el-form-item>
                <el-divider content-position="left">子场景独立附件</el-divider>
                <div v-for="cat in subFileCategories" :key="cat" class="mb-3">
                  <div class="flex items-center gap-2 mb-1">
                    <span class="w-20 text-sm font-medium text-gray-700">{{ cat }}</span>
                    <input
                      type="file" multiple class="block flex-1 text-xs"
                      @change="(e: any) => onSubScenarioFileFor(ss, e, cat)"
                    />
                  </div>
                  <div v-if="(ss.attachments.filter((a: any) => a.category === cat).length + (ss.inheritedFiles || []).filter((f: any) => f.category === cat).length)" class="ml-20">
                    <el-tag
                      v-for="(a, ai) in ss.attachments.filter((x: any) => x.category === cat)" :key="'u'+ai"
                      class="mr-2 mb-1"
                      type="info"
                      effect="plain"
                    >{{ a.file?.name }}<el-button
                        link type="danger" size="small" class="ml-1"
                        @click="ss.attachments.splice(ss.attachments.indexOf(a), 1)">×</el-button></el-tag>
                    <el-tag
                      v-for="(f, fi) in (ss.inheritedFiles || []).filter((x: any) => x.category === cat)" :key="'i'+fi"
                      class="mr-2 mb-1"
                      type="success"
                      effect="plain"
                    >继承 · {{ f.name }}
                      <el-button link type="primary" size="small" class="ml-1"
                        @click="downloadInheritedFile(f)"><el-icon class="mr-0.5"><Download /></el-icon>下载</el-button>
                    </el-tag>
                  </div>
                </div>
                <el-divider content-position="left">测试记录</el-divider>
                <div class="flex items-center gap-2">
                  <span class="w-20 text-sm font-medium text-gray-700">测试记录</span>
                  <input
                    type="file" multiple class="block flex-1 text-xs"
                    @change="(e: any) => onSubScenarioRecords(ss, e)"
                  />
                </div>
                <span class="text-xs text-gray-400 ml-20">已选 {{ ss.test_records?.length || 0 }} 个测试记录</span>
              </div>
              <el-button size="small" v-if="createForm.type !== 'standard'" @click="addSubScenario">+ 添加子场景</el-button>

              <template v-if="createForm.type === 'standard'">
                <el-form-item label="测试序列" required>
                  <el-select v-model="createForm.sequence_id" filterable clearable class="w-full" placeholder="选择测试序列">
                    <el-option v-for="s in sequences" :key="s.id" :label="s.name" :value="s.id" />
                  </el-select>
                </el-form-item>

                <el-divider>二进制文件</el-divider>
                <el-upload
                  ref="uploadRef"
                  :auto-upload="false"
                  :file-list="uploadFiles"
                  multiple
                  @change="handleUploadChange"
                >
                  <el-button size="small">选择文件</el-button>
                  <template #tip><span class="text-xs text-gray-400">上传后将随版本一起归档</span></template>
                </el-upload>
              </template>

              <el-form-item class="mt-4">
                <el-button type="primary" :loading="createSubmitting" @click="submitCreate">保存并进入发布</el-button>
                <el-button @click="cancelCreate">取消</el-button>
              </el-form-item>
            </el-form>
          </template>

          <!-- REVIEW MODE: review created version & submit for approval -->
          <template v-else>
            <div v-loading="releaseDetailLoading" v-if="releaseDetail">
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="版本类型">{{ typeLabel(releaseDetail.type) }}</el-descriptions-item>
                <el-descriptions-item label="状态">
                  <el-tag :type="versionStatusTag(releaseDetail.status)" size="small">{{ statusLabel(releaseDetail.status) }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="工程名称">{{ releaseDetail.project_name }}</el-descriptions-item>
                <el-descriptions-item label="版本号">{{ releaseDetail.version }}</el-descriptions-item>
                <el-descriptions-item label="BOM 编码">{{ releaseDetail.bom_code }}</el-descriptions-item>
                <el-descriptions-item label="TPS 名称">{{ releaseDetail.tps_name }}</el-descriptions-item>
                <el-descriptions-item label="描述" :span="2">{{ releaseDetail.description }}</el-descriptions-item>
              </el-descriptions>

              <el-divider>子场景</el-divider>
              <div v-for="ss in releaseDetail.sub_scenarios" :key="ss.id" class="border rounded p-3 mb-3">
                <div class="flex items-center justify-between mb-2">
                  <span class="font-bold">{{ ss.name }}</span>
                  <span class="text-xs text-gray-400">{{ ss.process_type }} / {{ ss.workstation }}</span>
                </div>
                <el-descriptions :column="1" size="small" border>
                  <el-descriptions-item label="测试序列">{{ seqName(ss.sequence_id) }}</el-descriptions-item>
                  <el-descriptions-item label="硬件参数">{{ JSON.stringify(ss.hardware_params) }}</el-descriptions-item>
                  <el-descriptions-item label="属性页">{{ JSON.stringify(ss.property_page) }}</el-descriptions-item>
                  <el-descriptions-item label="指标文件(JSON)">{{ ss.metrics_json || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="指标文件(INI)">{{ ss.metrics_ini || '-' }}</el-descriptions-item>
                </el-descriptions>
                <div class="mt-2">
                  <template v-for="cat in subFileCategories.concat('测试记录')" :key="cat">
                    <div v-if="filesByCat(ss.id, cat).length" class="mb-1 flex items-start">
                      <span class="text-xs text-gray-500 w-24 shrink-0 mt-1">{{ cat }}：</span>
                      <div class="flex flex-wrap gap-1">
                        <el-tag
                          v-for="f in filesByCat(ss.id, cat)" :key="f.id"
                          class="mr-1 mb-1"
                          size="small"
                          type="info"
                        >
                          {{ f.filename }}
                          <el-button link type="primary" size="small" class="ml-1"
                            @click="downloadSubFile(f)"><el-icon class="mr-0.5"><Download /></el-icon>下载</el-button>
                          <el-button link type="danger" size="small"
                            @click="deleteSubFile(f)">删除</el-button>
                        </el-tag>
                      </div>
                    </div>
                  </template>
                  <div v-if="!subScenarioFiles(ss.id).length" class="text-xs text-gray-400">暂无附件</div>
                </div>
              </div>

              <el-divider>审批（测试经理 / 项目经理）</el-divider>
              <el-form label-width="120px" v-loading="releaseSubmitting">
                <el-form-item label="测试经理审核">
                  <el-select v-model="releaseForm.test_manager" filterable class="w-full" placeholder="选择审批人">
                    <el-option v-for="u in allUsers" :key="u.id" :label="u.display_name || u.username" :value="u.display_name || u.username" />
                  </el-select>
                </el-form-item>
                <el-form-item label="项目经理审核">
                  <el-select v-model="releaseForm.project_manager" filterable class="w-full" placeholder="选择审批人">
                    <el-option v-for="u in allUsers" :key="u.id" :label="u.display_name || u.username" :value="u.display_name || u.username" />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <template v-if="releaseDetail.status === 'released'">
                    <el-alert type="success" :closable="false" show-icon title="版本已发布，可前往发行流程进行部署" class="mb-2 w-full" />
                    <el-button type="success" @click="goDeploy">
                      <el-icon class="mr-0.5"><Promotion /></el-icon>前往发行流程
                    </el-button>
                    <el-button @click="startCreate">新建版本</el-button>
                  </template>
                  <template v-else>
                    <el-button type="primary" :loading="releaseSubmitting" @click="submitRelease">
                      <el-icon class="mr-0.5"><Promotion /></el-icon>发布（分配审批并提交）
                    </el-button>
                    <el-button @click="startCreate">新建版本</el-button>
                  </template>
                </el-form-item>
              </el-form>
            </div>
          </template>
        </el-tab-pane>

        <!-- Tab 3: Version Deployment / Distribution -->
        <el-tab-pane name="deploy">
          <template #label><el-icon class="mr-1 align-middle"><Bottom /></el-icon>版本发行</template>
          <div class="app-card p-4 mb-4" v-loading="deploySubmitting">
            <div class="font-bold mb-3">创建版本发行（直接编辑，无需弹窗）</div>
            <el-form label-width="90px">
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="搜索版本" required>
                    <el-autocomplete
                      v-model="deploySearch"
                      :fetch-suggestions="queryDeployVersions"
                      placeholder="输入版本号/工程名自动索引"
                      clearable class="w-full"
                      @select="onPickDeployVersion"
                    />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="TE工程师">
                    <el-select v-model="deployTE" filterable clearable class="w-full" placeholder="发行审批人">
                      <el-option v-for="u in allUsers" :key="u.id" :label="u.display_name || u.username" :value="u.display_name || u.username" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="厂区">
                <div class="w-full flex items-center gap-2">
                  <el-select v-model="deployFactories" multiple filterable class="flex-1" placeholder="多选厂区" @change="onFactoryChange">
                    <el-option v-for="f in factories" :key="f.id" :label="f.name" :value="f.id" />
                  </el-select>
                  <el-button size="small" @click="selectAllFactories">全选厂区</el-button>
                </div>
              </el-form-item>
              <el-form-item label="线体">
                <el-select v-model="deployLines" multiple filterable class="w-full" placeholder="默认所选厂区全部线体，可取消" @change="onLineChange">
                  <el-option v-for="l in availableLines" :key="l.id" :label="l.name" :value="l.id" />
                </el-select>
                <span class="text-xs text-gray-400">可选；默认选中全部厂区线体</span>
              </el-form-item>
              <el-form-item label="装备">
                <el-select v-model="deployStations" multiple filterable class="w-full" placeholder="默认所选范围全部装备，可取消">
                  <el-option v-for="s in availableStations" :key="s.id" :label="s.name" :value="s.id" />
                </el-select>
                <span class="text-xs text-gray-400">可选；默认选中全部匹配装备</span>
              </el-form-item>
              <el-form-item label="下发范围">
                <el-table v-if="scopeRows.length" :data="scopeRows" size="small" stripe style="width: 100%">
                  <el-table-column prop="factory" label="厂区" />
                  <el-table-column prop="line" label="线体" />
                  <el-table-column prop="station" label="装备" />
                </el-table>
                <span v-else class="text-xs text-gray-400">请选择厂区 / 线体 / 装备</span>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="deploySubmitting" @click="submitDeployInline">
                  <el-icon class="mr-0.5"><Promotion /></el-icon>立即发行
                </el-button>
                <el-button @click="resetDeployForm">重置</el-button>
              </el-form-item>
            </el-form>
          </div>

          <el-table :data="deployVersions" v-loading="deployLoading" stripe style="width: 100%" size="small">
            <template #empty>
              <div class="flex flex-col items-center py-8 text-gray-400">
                <el-icon :size="36" color="#c0c8d4"><Box /></el-icon>
                <div class="mt-2 text-sm">暂无已发布版本可发行</div>
              </div>
            </template>
            <el-table-column prop="version" label="版本号" width="100" />
            <el-table-column prop="project_name" label="项目" width="120" show-overflow-tooltip />
            <el-table-column prop="type" label="类型" width="110">
              <template #default="{ row }">{{ typeLabel(row.type) }}</template>
            </el-table-column>
            <el-table-column prop="bom_code" label="BOM编码" width="120" show-overflow-tooltip />
            <el-table-column prop="created_by" label="创建人" width="90" />
            <el-table-column prop="created_at" label="创建时间" width="160" />
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="viewVersion(row)">
                  <el-icon class="mr-0.5"><View /></el-icon>查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- Tab 4: Pending Approvals -->
        <el-tab-pane name="approvals">
          <template #label><el-icon class="mr-1 align-middle"><Histogram /></el-icon>待审批</template>
          <el-timeline>
            <el-timeline-item
              v-for="item in pendingApprovals"
              :key="`${item.type}-${item.id}`"
              :timestamp="item.created_at || ''"
              :color="item.type === 'deployment' ? '#E6A23C' : '#409EFF'"
            >
              <div class="flex items-center justify-between">
                <div>
                  <p class="font-bold">{{ item.title || item.version || '审批' }}</p>
                  <p class="text-sm text-gray-500">
                    {{ item.type === 'deployment' ? '部署审批' : '版本审批' }}
                    — {{ item.assigned_to || item.approver || '-' }}
                  </p>
                </div>
                <div class="flex gap-2">
                  <el-input
                    v-if="item.type === 'deployment' && item.status === 'pending'"
                    v-model="approveComment"
                    placeholder="审批意见"
                    size="small"
                    style="width: 200px"
                  />
                  <el-button
                    v-if="item.type !== 'deployment' || item.status === 'pending'"
                    size="small" type="success"
                    @click="handleApprove(item)"
                  >通过</el-button>
                  <el-button
                    v-if="item.type === 'deployment' && item.status === 'approved'"
                    size="small" type="primary"
                    @click="handleExecute(item)"
                  >执行部署</el-button>
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
          <div v-if="pendingApprovals.length === 0" class="flex flex-col items-center py-12 text-gray-400">
            <el-icon :size="36" color="#c0c8d4"><CircleCheck /></el-icon>
            <div class="mt-2 text-sm">暂无待审批事项</div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- Deploy Dialog -->

    <!-- Version Detail Dialog -->
    <el-dialog v-model="detailVisible" title="版本详情" width="700px">
      <div v-if="detailData" v-loading="detailLoading">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="版本号">{{ detailData.version }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ detailData.status }}</el-descriptions-item>
          <el-descriptions-item label="项目">{{ detailData.project_name }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ typeLabel(detailData.type) }}</el-descriptions-item>
          <el-descriptions-item label="BOM编码">{{ detailData.bom_code }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ detailData.created_by }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ detailData.description }}</el-descriptions-item>
        </el-descriptions>

        <template v-if="detailData.sub_scenarios?.length">
          <el-divider>子场景</el-divider>
          <div v-for="ss in detailData.sub_scenarios" :key="ss.id" class="border rounded p-3 mb-3">
            <div class="flex items-center justify-between mb-2">
              <span class="font-bold">{{ ss.name }}</span>
              <span class="text-xs text-gray-400">{{ ss.process_type }} / {{ ss.workstation }}</span>
            </div>
            <template v-for="cat in subFileCategories.concat('测试记录')" :key="cat">
              <div v-if="detailFilesByCat(ss.id, cat).length" class="mb-1 flex items-start">
                <span class="text-xs text-gray-500 w-24 shrink-0 mt-1">{{ cat }}：</span>
                <div class="flex flex-wrap gap-1">
                  <el-tag
                    v-for="f in detailFilesByCat(ss.id, cat)" :key="f.id"
                    class="mr-1 mb-1" size="small" type="info"
                  >
                    {{ f.filename }}
                    <el-button link type="primary" size="small" class="ml-1" @click="downloadDetailFile(f)"><el-icon class="mr-0.5"><Download /></el-icon>下载</el-button>
                  </el-tag>
                </div>
              </div>
            </template>
            <div v-if="!detailSubFiles(ss.id).length" class="text-xs text-gray-400">暂无附件</div>
          </div>
        </template>
        <template v-else>
          <el-divider>二进制文件</el-divider>
          <template v-for="cat in subFileCategories.concat('测试记录', '附件')" :key="cat">
            <div v-if="detailGeneralFiles(cat).length" class="mb-1 flex items-start">
              <span class="text-xs text-gray-500 w-24 shrink-0 mt-1">{{ cat }}：</span>
              <div class="flex flex-wrap gap-1">
                <el-tag
                  v-for="f in detailGeneralFiles(cat)" :key="f.id"
                  class="mr-1 mb-1" size="small" type="info"
                >
                  {{ f.filename }}
                  <el-button link type="primary" size="small" class="ml-1" @click="downloadDetailFile(f)"><el-icon class="mr-0.5"><Download /></el-icon>下载</el-button>
                </el-tag>
              </div>
            </div>
          </template>
          <div v-if="!(detailData.binary_files || []).length" class="text-gray-400 text-center py-4">无文件</div>
        </template>

        <el-divider>部署记录</el-divider>
        <el-table :data="detailData.deployments || []" size="small" stripe>
          <el-table-column prop="station_name" label="目标工站" />
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status === 'approved' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="assigned_to" label="审批人" width="100" />
          <el-table-column prop="created_at" label="创建时间" width="160" />
        </el-table>
        <div v-if="!detailData.deployments?.length" class="text-gray-400 text-center py-4">无部署记录</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { versionApi } from '@/api/version'
import { testApi } from '@/api/test'
import { stationApi } from '@/api/station'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadInstance } from 'element-plus'
import {
  Plus, Search, Document, Promotion, List,
  Download, Delete, RefreshLeft, View, Bottom, FolderOpened,
  Loading, Box, Histogram, Edit, Warning, CircleCheck, Refresh,
} from '@element-plus/icons-vue'

const authStore = useAuthStore()
const currentUser = authStore.user

const activeTab = ref('list')

function typeLabel(type: string): string {
  const map: Record<string, string> = {
    standard: '标准', multi_process: '多工序版本', product_family: '产品族版本',
  }
  return map[type] || type
}

// ── Version List ──
const versions = ref<any[]>([])
const versionsLoading = ref(false)
const versionPage = ref(1)
const versionPageSize = ref(20)
const versionTotal = ref(0)
const listFilters = reactive({ status: '', project_name: '' })
const listScope = ref<'mine' | 'all'>('mine')

function versionStatusTag(status: string): string {
  const map: Record<string, string> = {
    draft: 'info', released: 'success', deployed: 'primary', delisted: 'danger',
  }
  return map[status] || 'info'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    draft: '草稿', released: '已发布', deployed: '已发行', delisted: '已下架',
  }
  return map[status] || status
}

function onScopeChange() {
  versionPage.value = 1
  fetchVersions()
}

async function fetchVersions() {
  versionsLoading.value = true
  try {
    const params: any = { page: versionPage.value, page_size: versionPageSize.value }
    if (listFilters.status) params.status = listFilters.status
    if (listFilters.project_name) params.project_name = listFilters.project_name
    if (listScope.value === 'mine') params.scope = 'mine'
    const res = await versionApi.list(params)
    versions.value = res.data?.items || []
    versionTotal.value = res.data?.total || 0
  } catch (e: any) {
    console.error('加载版本列表失败', e)
  } finally {
    versionsLoading.value = false
  }
}

async function handleDelist(row: any) {
  try {
    await ElMessageBox.confirm(`确定下架版本 "${row.version}"？`, '确认')
    await versionApi.delist(row.id)
    ElMessage.success('版本已下架')
    await fetchVersions()
  } catch { /* cancelled */ }
}

async function handleRestore(row: any) {
  await versionApi.restore(row.id)
  ElMessage.success('版本已恢复')
  await fetchVersions()
}

async function handleDeleteVersion(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除版本 "${row.version}"？`, '确认', { type: 'warning' })
    await versionApi.deleteVersion(row.id)
    ElMessage.success('版本已删除')
    await fetchVersions()
  } catch { /* cancelled */ }
}

// ── Version Detail ──
const detailVisible = ref(false)
const detailData = ref<any>(null)
const detailLoading = ref(false)

async function viewVersion(row: any) {
  detailLoading.value = true
  detailVisible.value = true
  try {
    const res = await versionApi.get(row.id)
    detailData.value = res.data || {}
  } finally {
    detailLoading.value = false
  }
}

// ── Create / Edit Version (版本发布 create mode) ──
const editMode = ref(false)
const createLoading = ref(false)
const createSubmitting = ref(false)
const existingVersions = ref<any[]>([])
const sequences = ref<any[]>([])
const allUsers = ref<any[]>([])
const subScenarioPresets = ref<string[]>([])
const uploadRef = ref<UploadInstance>()
const uploadFiles = ref<any[]>([])

// 版本发布 tab mode: 'create' (build) | 'review' (after created)
const releaseMode = ref<'create' | 'review'>('create')
const releaseDetail = ref<any>(null)
const releaseDetailLoading = ref(false)

const createForm = reactive({
  version: '', project_name: '', description: '', type: 'standard',
  process_type: '', workstation: '', codes_config: [] as any[], bom_code: '',
  tps_name: '', sequence_id: 0, inherit_from_id: null as number | null,
  auto_inherit: false, domain_tags: '',
  sub_scenarios: [] as any[],
  approval_steps: [] as any[],
})
const currentEditingId = ref<number | null>(null)

function newSubScenario(): any {
  return {
    name: '', process_type: '', workstation: '', sequence_id: 0,
    hardware_params: '{}', property_page: '{}', software_metrics: [],
    metrics_json: '', metrics_ini: '',
    attachments: [] as any[], test_records: [] as any[],
    inheritedFiles: [] as any[],
  }
}

function addSubScenario() {
  createForm.sub_scenarios.push(newSubScenario())
}

function addPresetScenario(preset: string) {
  const name = preset.toUpperCase()
  if (createForm.sub_scenarios.some((s: any) => (s.name || '').toUpperCase() === name)) return
  createForm.sub_scenarios.push({ ...newSubScenario(), name })
}

function onTypeChange() {
  if (createForm.type === 'standard') {
    createForm.sub_scenarios = []
  } else {
    createForm.sequence_id = 0
    createForm.approval_steps = []
  }
}

function addApprovalStep() {
  createForm.approval_steps.push({
    step_name: '', approver: '', sort_order: createForm.approval_steps.length + 1,
  })
}

function handleUploadChange(uploadFile: any) {
  uploadFiles.value = uploadFile.raw ? [uploadFile] : []
}

const subFileCategories = ['硬件参数', '软件指标', '产品属性', '配置文件', '其它']

const inheritSource = ref<any>(null)

function onSubScenarioFileFor(ss: any, e: any, cat: string) {
  const files = Array.from(e.target.files || []) as any[]
  for (const f of files) {
    ss.attachments.push({ file: f, category: cat, name: f.name })
  }
  e.target.value = ''
}

function onInheritChange(id: number | null) {
  inheritSource.value = null
  if (!id) {
    if (!createForm.auto_inherit) resetInheritedConfig()
    return
  }
  versionApi.get(id).then((res: any) => {
    inheritSource.value = res.data || {}
    applyInheritConfig(inheritSource.value)
  }).catch(() => {})
}

function applyInheritConfig(src: any) {
  if (!src) return
  createForm.type = src.type
  if (!createForm.bom_code) createForm.bom_code = src.bom_code || ''
  if (!createForm.tps_name) createForm.tps_name = src.tps_name || ''
  if (!createForm.description) createForm.description = src.description || ''
  createForm.domain_tags = (src.domain_tags || '')
  if (createForm.type !== 'standard' && !createForm.sub_scenarios.length && src.sub_scenarios?.length) {
    const srcFilesBySs: Record<number, any[]> = {}
    for (const f of (src.binary_files || [])) {
      const sid = f.sub_scenario_id || 0
      srcFilesBySs[sid] = srcFilesBySs[sid] || []
      srcFilesBySs[sid].push(f)
    }
    const srcByName: Record<string, any> = {}
    for (const s of (src.sub_scenarios || [])) srcByName[(s.name || '').toUpperCase()] = s
    createForm.sub_scenarios = src.sub_scenarios.map((s: any) => {
      const ns: any = {
        ...newSubScenario(),
        name: s.name, process_type: s.process_type, workstation: s.workstation,
        sequence_id: s.sequence_id || 0,
        hardware_params: typeof s.hardware_params === 'string' ? s.hardware_params : JSON.stringify(s.hardware_params || {}),
        property_page: typeof s.property_page === 'string' ? s.property_page : JSON.stringify(s.property_page || {}),
        metrics_json: s.metrics_json || '', metrics_ini: s.metrics_ini || '',
      }
      const srcId = srcByName[(s.name || '').toUpperCase()]?.id
      ns.inheritedFiles = (srcFilesBySs[srcId] || []).map((f: any) => ({
        id: f.id, version_id: src.id, name: f.filename, category: f.description || '附件',
      }))
      return ns
    })
  }
}

function resetInheritedConfig() {
  createForm.bom_code = ''
  createForm.tps_name = ''
  createForm.domain_tags = ''
  if (createForm.type !== 'standard') createForm.sub_scenarios = []
}

// 1. 工程名称智能联想：从已存在版本中匹配工程名称
const projectNameOptions = computed(() => {
  const set = new Set<string>()
  for (const v of existingVersions.value) {
    if (v.project_name) set.add(v.project_name)
  }
  return Array.from(set).map((n) => ({ value: n }))
})
function queryProjectNames(q: string, cb: any) {
  const kw = (q || '').toLowerCase()
  const list = projectNameOptions.value.filter((o) => o.value.toLowerCase().includes(kw))
  cb(list)
}
function onSubScenarioRecords(ss: any, e: any) {
  ss.test_records = Array.from(e.target.files || [])
}

function resetCreateForm() {
  Object.assign(createForm, {
    version: '', project_name: '', description: '', type: 'standard',
    process_type: '', workstation: '', codes_config: [], bom_code: '',
    tps_name: '', sequence_id: 0, inherit_from_id: null, auto_inherit: false,
    domain_tags: '', sub_scenarios: [], approval_steps: [],
  })
  uploadFiles.value = []
}

function cancelCreate() {
  resetCreateForm()
  releaseMode.value = 'create'
  activeTab.value = 'list'
}

function startCreate() {
  editMode.value = false
  currentEditingId.value = null
  resetCreateForm()
  releaseMode.value = 'create'
  activeTab.value = 'release'
}

async function editVersion(row: any) {
  editMode.value = true
  currentEditingId.value = row.id
  Object.assign(createForm, {
    version: row.version, project_name: row.project_name, description: row.description,
    type: row.type, process_type: row.process_type, workstation: row.workstation,
    bom_code: row.bom_code, tps_name: row.tps_name, sequence_id: row.sequence_id,
    inherit_from_id: null, auto_inherit: false, sub_scenarios: [], approval_steps: [],
  })
  releaseMode.value = 'create'
  activeTab.value = 'release'
}

async function onProjectNameBlur() {
  const name = createForm.project_name.trim()
  if (!name) return
  // 3.1 继承源必须与当前工程一致；工程变更则清除已选基版
  if (inheritSource.value && inheritSource.value.project_name !== name) {
    createForm.inherit_from_id = null
    inheritSource.value = null
    resetInheritedConfig()
  }
  // 2. 同工程版本号自动递增（不同工程相互独立）
  try {
    const res = await versionApi.nextVersion(name)
    if (res.data?.version) createForm.version = res.data.version
  } catch { /* ignore */ }
  // 自动继承开关：选同一工程最新版本作为基版
  if (createForm.auto_inherit && !createForm.inherit_from_id) {
    const r = await versionApi.list({ page: 1, page_size: 5, project_name: name })
    const items = r.data?.items || []
    if (items.length) {
      createForm.inherit_from_id = items[0].id
      onInheritChange(items[0].id)
    }
  }
}

async function onAutoInheritChange(val: any) {
  if (val) {
    const name = createForm.project_name.trim()
    if (!name) { ElMessage.warning('请先输入工程名称'); createForm.auto_inherit = false; return }
    const r = await versionApi.list({ page: 1, page_size: 5, project_name: name })
    const items = r.data?.items || []
    if (items.length) {
      createForm.inherit_from_id = items[0].id
      onInheritChange(items[0].id)
      ElMessage.info(`已自动继承同一工程上一版本 #${items[0].id}（${items[0].version}）配置`)
    } else {
      createForm.auto_inherit = false
      ElMessage.info('未找到可继承的同一工程历史版本')
    }
  } else {
    createForm.inherit_from_id = null
    onInheritChange(null)
  }
}

async function submitCreate() {
  if (!createForm.project_name) { ElMessage.warning('请输入项目名称'); return }
  if (!createForm.version) { ElMessage.warning('请输入版本号'); return }
  if (createForm.type !== 'standard') {
    if (!createForm.bom_code) { ElMessage.warning('多工序/产品族版本必须填写BOM编码'); return }
    if (createForm.sub_scenarios.length === 0) { ElMessage.warning('多工序/产品族版本必须至少添加一个子场景'); return }
  }

  createSubmitting.value = true
  try {
    const data: any = { ...createForm }
    delete (data as any).auto_inherit

    if (createForm.type !== 'standard' && createForm.sub_scenarios.length > 0) {
      data.codes_config = createForm.sub_scenarios.map((ss: any) => ({
        name: (ss.name || '').toUpperCase(),
        hardware_params: parseJSON(ss.hardware_params),
        property_page: parseJSON(ss.property_page),
        process_type: ss.process_type,
        workstation: ss.workstation,
        sequence_id: ss.sequence_id,
        metrics_json: ss.metrics_json || '',
        metrics_ini: ss.metrics_ini || '',
      }))
    }

    let res
    if (editMode.value && currentEditingId.value) {
      res = await versionApi.update(currentEditingId.value, data)
    } else {
      res = await versionApi.create(data)
    }
    const versionId = res.data?.id ?? currentEditingId.value

    if (!editMode.value && versionId) {
      // Version-level binaries (standard type)
      if (uploadFiles.value.length > 0) {
        const formData = new FormData()
        formData.append('file', (uploadFiles.value[0] as any).raw || uploadFiles.value[0])
        await versionApi.uploadBinary(versionId, formData)
      }
      // Per-sub-scenario binaries + test records
      const detail = await versionApi.get(versionId)
      const ssList: any[] = detail.data?.sub_scenarios || []
      const uploadOne = async (file: any, ssId: number) => {
        const fd = new FormData()
        fd.append('file', file)
        await versionApi.uploadBinary(versionId, fd, ssId)
      }
      for (const ss of createForm.sub_scenarios) {
        const target = ssList.find((s: any) => (s.name || '').toUpperCase() === (ss.name || '').toUpperCase())
        if (!target) continue
        for (const a of (ss.attachments || [])) {
          const fd = new FormData()
          fd.append('file', a.file)
          fd.append('description', a.category || '附件')
          await versionApi.uploadBinary(versionId, fd, target.id)
        }
        for (const f of (ss.test_records || [])) {
          const fd = new FormData()
          fd.append('file', f)
          fd.append('description', '测试记录')
          await versionApi.uploadBinary(versionId, fd, target.id)
        }
      }
      if (createForm.approval_steps.length > 0) {
        const tm = createForm.approval_steps.find((s: any) => s.step_name?.includes('测试经理'))
        const pm = createForm.approval_steps.find((s: any) => s.step_name?.includes('项目经理'))
        await versionApi.assignApprovers(versionId, {
          test_manager: tm?.approver || '',
          project_manager: pm?.approver || '',
        })
      }
      await loadReleaseDetail(versionId)
      ElMessage.success('版本创建成功，已进入发布流程')
    } else {
      ElMessage.success('版本已更新')
      resetCreateForm()
      releaseMode.value = 'create'
    }
    await Promise.all([fetchVersions(), fetchDeployVersions()])
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    createSubmitting.value = false
  }
}

function parseJSON(str: string): any {
  try { return JSON.parse(str) } catch { return str }
}

// ── Release (版本发布 review mode) ──
const releaseSubmitting = ref(false)
const releaseForm = reactive({
  versionId: 0, version_label: '', test_manager: '', project_manager: '',
})

function subScenarioFiles(ssId: number): any[] {
  return (releaseDetail.value?.binary_files || []).filter((f: any) => f.sub_scenario_id === ssId)
}

function filesByCat(ssId: number, cat: string): any[] {
  return subScenarioFiles(ssId).filter((f: any) => (f.description || '附件') === cat)
}

function seqName(id: number): string {
  if (!id) return '-'
  const s = sequences.value.find((x: any) => x.id === id)
  return s ? s.name : `#${id}`
}

async function loadReleaseDetail(id: number) {
  releaseDetailLoading.value = true
  releaseMode.value = 'review'
  try {
    const res = await versionApi.get(id)
    releaseDetail.value = res.data || {}
    releaseForm.versionId = id
    releaseForm.version_label = `${res.data?.version} — ${res.data?.project_name}`
    releaseForm.test_manager = currentUser?.display_name || currentUser?.username || ''
    releaseForm.project_manager = currentUser?.display_name || currentUser?.username || ''
  } catch (e: any) {
    ElMessage.error('加载版本详情失败')
  } finally {
    releaseDetailLoading.value = false
  }
}

async function submitRelease() {
  if (!releaseForm.test_manager || !releaseForm.project_manager) {
    ElMessage.warning('请选择审批人')
    return
  }
  releaseSubmitting.value = true
  try {
    const id = releaseForm.versionId
    await versionApi.assignApprovers(id, {
      test_manager: releaseForm.test_manager,
      project_manager: releaseForm.project_manager,
    })
    const detail = await versionApi.get(id)
    const steps: any[] = (detail.data?.steps || []).filter((s: any) => s.stage === 1)
    for (const s of steps) {
      await versionApi.submitStep(id, { step_id: s.id, comment: '' })
    }
    ElMessage.success('版本发布成功，已自动通过审批并发布，可在「版本发行」查看')
    const updated = await versionApi.get(id)
    releaseDetail.value = updated.data || {}
    await Promise.allSettled([fetchDeployVersions(), loadPendingApprovals(), fetchVersions()])
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '发布失败')
  } finally {
    releaseSubmitting.value = false
  }
}

// 4. 子场景附件：在线查看/下载/删除
function downloadSubFile(f: any) {
  const vid = releaseDetail.value?.id
  if (!vid) return
  window.open(versionApi.downloadBinaryUrl(vid, f.id), '_blank')
}

function downloadDetailFile(f: any) {
  const vid = detailData.value?.id
  if (!vid) return
  window.open(versionApi.downloadBinaryUrl(vid, f.id), '_blank')
}

function downloadInheritedFile(f: any) {
  if (!f.version_id || !f.id) return
  window.open(versionApi.downloadBinaryUrl(f.version_id, f.id), '_blank')
}

function detailSubFiles(ssId: number): any[] {
  return (detailData.value?.binary_files || []).filter((f: any) => f.sub_scenario_id === ssId)
}
function detailFilesByCat(ssId: number, cat: string): any[] {
  return detailSubFiles(ssId).filter((f: any) => (f.description || '附件') === cat)
}
function detailGeneralFiles(cat: string): any[] {
  return (detailData.value?.binary_files || [])
    .filter((f: any) => (f.sub_scenario_id || 0) === 0 && (f.description || '附件') === cat)
}

async function deleteSubFile(f: any) {
  const vid = releaseDetail.value?.id
  if (!vid) return
  try {
    await versionApi.deleteBinary(vid, f.id)
    ElMessage.success('附件已删除')
    await loadReleaseDetail(vid)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '删除失败')
  }
}

function goDeploy() {
  activeTab.value = 'deploy'
}

function goDeployWith(row: any) {
  deploySearch.value = `${row.version} — ${row.project_name}`
  deployVersionId.value = row.id
  activeTab.value = 'deploy'
  inheritTargets(row.id)
}

// ── Deployment / Distribution (版本发行) ──
const deployVersions = ref<any[]>([])
const deployLoading = ref(false)
const deploySubmitting = ref(false)
const deploySearch = ref('')
const deployVersionId = ref<number | null>(null)
const deployTE = ref('')
const deployFactories = ref<number[]>([])
const deployLines = ref<number[]>([])
const deployStations = ref<number[]>([])
const factories = ref<any[]>([])
const allLines = ref<any[]>([])
const allStations = ref<any[]>([])

const lineFactory = computed(() => {
  const m: Record<number, number> = {}
  for (const l of allLines.value) m[l.id] = l.factory_id
  return m
})

const availableLines = computed(() =>
  deployFactories.value.length
    ? allLines.value.filter((l: any) => deployFactories.value.includes(l.factory_id))
    : allLines.value
)

const availableStations = computed(() => {
  if (deployLines.value.length) {
    return allStations.value.filter((s: any) => deployLines.value.includes(s.line_id))
  }
  if (deployFactories.value.length) {
    return allStations.value.filter((s: any) => deployFactories.value.includes(lineFactory.value[s.line_id]))
  }
  return allStations.value
})

const deployScopeText = computed(() =>
  `厂区 ${deployFactories.value.length} 个｜线体 ${deployLines.value.length} 条｜装备 ${deployStations.value.length} 台`
)

const scopeRows = computed(() => {
  const fn = (id: number) => (factories.value.find((x: any) => x.id === id) || {}).name || ''
  const ln = (id: number) => (allLines.value.find((x: any) => x.id === id) || {}).name || ''
  const sn = (id: number) => (allStations.value.find((x: any) => x.id === id) || {}).name || ''
  if (deployStations.value.length) {
    return deployStations.value.map((sid: number) => {
      const st: any = allStations.value.find((x: any) => x.id === sid) || {}
      const lid = st.line_id
      const fid = lid != null ? lineFactory.value[lid] : null
      return { factory: fn(fid || 0), line: ln(lid), station: sn(sid) }
    })
  }
  if (deployLines.value.length) {
    return deployLines.value.map((lid: number) => ({
      factory: fn(lineFactory.value[lid]), line: ln(lid), station: '-',
    }))
  }
  return deployFactories.value.map((fid: number) => ({ factory: fn(fid), line: '-', station: '-' }))
})

async function loadDeployHierarchy() {
  try {
    const [f, l, s] = await Promise.all([
      stationApi.listFactories(),
      stationApi.listLines(),
      stationApi.listStations(),
    ])
    factories.value = f.data || []
    allLines.value = l.data || []
    allStations.value = s.data || []
  } catch { /* ignore */ }
}

async function fetchDeployVersions() {
  deployLoading.value = true
  try {
    const [released, deployed] = await Promise.all([
      versionApi.list({ page: 1, page_size: 200, status: 'released' }),
      versionApi.list({ page: 1, page_size: 200, status: 'deployed' }),
    ])
    const releasedItems = (released as any).data?.items || []
    const deployedItems = (deployed as any).data?.items || []
    // merge, newer first
    const merged = [...releasedItems, ...deployedItems]
    merged.sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    deployVersions.value = merged
  } catch (e: any) {
    console.error('加载可发行版本列表失败', e)
  } finally {
    deployLoading.value = false
  }
}

function selectAllFactories() {
  deployFactories.value = factories.value.map((f: any) => f.id)
  onFactoryChange()
}

function onFactoryChange() {
  deployLines.value = availableLines.value.map((l: any) => l.id)
  deployStations.value = availableStations.value.map((s: any) => s.id)
}

function onLineChange() {
  deployStations.value = availableStations.value.map((s: any) => s.id)
}

function queryDeployVersions(q: string, cb: any) {
  const kw = (q || '').toLowerCase()
  const list = (deployVersions.value || [])
    .filter((v: any) => `${v.version} ${v.project_name}`.toLowerCase().includes(kw))
    .map((v: any) => ({ value: `${v.version} — ${v.project_name}`, id: v.id }))
  cb(list)
}

async function onPickDeployVersion(item: any) {
  deployVersionId.value = item.id
  deploySearch.value = item.value
  await inheritTargets(item.id)
}

async function inheritTargets(id: number) {
  if (!factories.value.length) await loadDeployHierarchy()
  try {
    const res = await versionApi.get(id)
    const deps = res.data?.deployments || []
    if (!deps.length) return
    const fIds = [...new Set(deps.map((d: any) => d.factory_id).filter(Boolean))] as number[]
    const lIds = [...new Set(deps.map((d: any) => d.line_id).filter(Boolean))] as number[]
    const sIds = [...new Set(deps.map((d: any) => d.station_id).filter(Boolean))] as number[]
    if (fIds.length) deployFactories.value = fIds.filter((f: number) => factories.value.some((x: any) => x.id === f))
    if (lIds.length) deployLines.value = lIds.filter((l: number) => allLines.value.some((x: any) => x.id === l))
    if (sIds.length) deployStations.value = sIds.filter((s: number) => allStations.value.some((x: any) => x.id === s))
    if (fIds.length) ElMessage.info(`已继承该版本上次发行的 ${fIds.length} 个厂区范围`)
  } catch { /* ignore */ }
}

function resetDeployForm() {
  deploySearch.value = ''
  deployVersionId.value = null
  deployTE.value = ''
  deployFactories.value = []
  deployLines.value = []
  deployStations.value = []
}

function buildDeployTargets(): any[] {
  const nameOf = (arr: any[], id: number) => (arr.find((x: any) => x.id === id) || {}).name || ''
  const targets: any[] = []
  const te = deployTE.value
  if (deployStations.value.length) {
    for (const sid of deployStations.value) {
      const st: any = allStations.value.find((x: any) => x.id === sid) || {}
      const lid = st.line_id
      const fid = lid != null ? lineFactory.value[lid] : null
      targets.push({
        station_id: sid, station_name: nameOf(allStations.value, sid),
        line_id: lid || 0, line_name: nameOf(allLines.value, lid),
        factory_id: fid || 0, factory_name: nameOf(factories.value, fid || 0),
        assign_te: !!te,
      })
    }
  } else if (deployLines.value.length) {
    for (const lid of deployLines.value) {
      const fid = lineFactory.value[lid]
      targets.push({
        line_id: lid, line_name: nameOf(allLines.value, lid),
        factory_id: fid || 0, factory_name: nameOf(factories.value, fid),
        assign_te: !!te,
      })
    }
  } else {
    for (const fid of deployFactories.value) {
      targets.push({
        factory_id: fid, factory_name: nameOf(factories.value, fid),
        assign_te: !!te,
      })
    }
  }
  return targets
}

async function submitDeployInline() {
  if (!deployVersionId.value) { ElMessage.warning('请先搜索并选择版本'); return }
  if (!deployTE.value) { ElMessage.warning('请选择 TE 工程师（发行审批人）'); return }
  if (!deployFactories.value.length && !deployLines.value.length && !deployStations.value.length) {
    ElMessage.warning('请至少选择一个厂区 / 线体 / 装备'); return
  }
  deploySubmitting.value = true
  try {
    await versionApi.createDeployment(deployVersionId.value!, {
      te_engineer: deployTE.value,
      targets: buildDeployTargets(),
    })
    ElMessage.success('发行申请已创建，请在「待审批」中审批并执行')
    resetDeployForm()
    await Promise.all([fetchDeployVersions(), loadPendingApprovals()])
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '创建发行失败')
  } finally {
    deploySubmitting.value = false
  }
}

// ── Pending Approvals ──
const pendingApprovals = ref<any[]>([])
const approveComment = ref('')

async function loadPendingApprovals() {
  try {
    const res = await versionApi.pendingApprovals()
    const items: any[] = res.data || []
    pendingApprovals.value = items.map((i: any) => {
      if (i.type === 'deployment') {
        return {
          type: 'deployment',
          id: i.dep_id,
          status: i.status || 'pending',
          title: i.version?.project_name || i.version?.version || '部署审批',
          version: i.version?.version || '',
          assigned_to: i.assigned_to || '',
          created_at: i.created_at || '',
        }
      }
      const s = i.step || {}
      return {
        type: 'step',
        id: s.id,
        step_id: s.id,
        version_id: s.version_id,
        title: i.version?.project_name || i.version?.version || '版本审批',
        version: i.version?.version || '',
        assigned_to: s.assigned_to || s.approver || '',
        created_at: s.created_at || i.version?.created_at || '',
      }
    })
  } catch { /* ignore */ }
}

async function handleApprove(item: any) {
  try {
    if (item.type === 'step') {
      await versionApi.submitStep(item.version_id || item.versionId, {
        step_id: item.id, comment: '',
      })
      ElMessage.success('审批通过')
    } else {
      await versionApi.approveDeployment(item.id, { comment: approveComment.value })
      ElMessage.success('部署已审批')
    }
    await Promise.all([loadPendingApprovals(), fetchDeployVersions(), fetchVersions()])
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '审批失败')
  }
}

async function handleExecute(item: any) {
  try {
    await versionApi.executeDeployment(item.id)
    ElMessage.success('部署执行成功')
    await Promise.all([loadPendingApprovals(), fetchDeployVersions(), fetchVersions()])
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '部署执行失败')
  }
}

onMounted(async () => {
  await Promise.all([
    fetchVersions(),
    fetchDeployVersions(),
    loadPendingApprovals(),
    versionApi.list({ page: 1, page_size: 100 }).then(r => { existingVersions.value = r.data?.items || [] }).catch(() => {}),
    testApi.listSequences().then(r => { sequences.value = r.data || [] }).catch(() => {}),
    versionApi.allUsers().then(r => { allUsers.value = r.data || [] }).catch(() => {}),
    versionApi.subScenarioPresets().then(r => { subScenarioPresets.value = r.data?.presets || [] }).catch(() => {}),
    loadDeployHierarchy(),
  ])
})
</script>
