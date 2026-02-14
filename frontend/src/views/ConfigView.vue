<template>
  <div class="config-view">
    <el-page-header @back="$router.back()">
      <template #content>
        <span class="page-title">系统配置</span>
      </template>
    </el-page-header>
    
    <el-card style="margin-top: 20px">
      <el-alert
        title="配置管理功能开发中..."
        type="info"
        :closable="false"
      />
    </el-card>
  </div>
</template>

<script setup>
// 配置管理页面
</script>

<style scoped>
.config-view {
  padding: 20px;
}

.page-title {
  font-size: 18px;
  font-weight: 500;
}
</style>
