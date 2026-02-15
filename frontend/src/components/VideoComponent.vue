<template>
  <node-view-wrapper class="video-wrapper">
    <div 
      class="video-container"
      :class="{ 'selected': selected }"
      @click="selectNode"
    >
      <video 
        :src="node.attrs.src" 
        :width="node.attrs.width"
        controls
        @click.stop
      >
        <source :src="node.attrs.src" type="video/mp4">
        您的浏览器不支持视频播放
      </video>
      <div v-if="selected" class="video-actions">
        <button @click.stop="deleteNode" class="delete-btn">删除</button>
      </div>
    </div>
  </node-view-wrapper>
</template>

<script setup>
import { NodeViewWrapper } from '@tiptap/vue-3'
import { computed } from 'vue'

const props = defineProps({
  node: {
    type: Object,
    required: true,
  },
  selected: {
    type: Boolean,
    default: false,
  },
  deleteNode: {
    type: Function,
    required: true,
  },
  updateAttributes: {
    type: Function,
    required: true,
  },
})

const selectNode = () => {
  // 选中节点
}
</script>

<style scoped>
.video-wrapper {
  margin: 1em 0;
}

.video-container {
  position: relative;
  border-radius: 4px;
  transition: all 0.2s;
}

.video-container.selected {
  outline: 2px solid #409eff;
  outline-offset: 2px;
}

.video-container video {
  max-width: 100%;
  height: auto;
  display: block;
  border-radius: 4px;
}

.video-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 8px;
}

.delete-btn {
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #f56c6c;
}

.delete-btn:hover {
  background: #f56c6c;
  color: white;
  border-color: #f56c6c;
}
</style>
