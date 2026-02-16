<template>
  <div class="tiptap-editor-root" ref="rootRef">
    <!-- 工具栏 -->
    <div class="tiptap-toolbar" v-if="editor">
      <button
        v-for="btn in toolbarButtons"
        :key="btn.action"
        :class="['tb-btn', { active: btn.isActive?.() }]"
        :title="btn.title"
        @click="btn.command"
      >
        <span v-html="btn.icon"></span>
      </button>
    </div>
    <!-- 编辑区 -->
    <div class="tiptap-content-wrap">
      <editor-content :editor="editor" class="tiptap-content" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import TextAlign from '@tiptap/extension-text-align'
import { Video } from './VideoExtension.js'

const props = defineProps({
  modelValue: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'change'])

const rootRef = ref(null)

const editor = useEditor({
  content: props.modelValue || '<p></p>',
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3, 4] },
      link: {
        openOnClick: false,
      },
    }),
    Image.configure({ inline: false, allowBase64: true }),
    Video,
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
  ],
  editorProps: {
    transformPastedHTML(html) {
      // 保留 Word 粘贴的格式和图片
      if (!html) return html
      
      // 保留图片（包括 base64 和 URL）
      // Tiptap Image 扩展会自动处理 <img> 标签，包括 base64 图片
      
      // 保留 Word 的列表格式（ol, ul, li）
      // 保留标题（h1-h6）
      // 保留基本格式标签（strong, em, u, s）
      // 保留段落（p）
      // 保留换行（br）
      
      // 清理 Word 特有的无用标签和样式，但保留内容结构
      let cleaned = html
      
      // 移除 Word 的注释和元数据
      cleaned = cleaned.replace(/<!--[\s\S]*?-->/g, '')
      
      // 移除完全空的段落，但保留有内容的
      cleaned = cleaned.replace(/<p[^>]*>\s*(&nbsp;|\s)*<\/p>/gi, '')
      
      // 保留表格结构（如果有）
      // 保留链接（a 标签）
      
      // 处理图片：移除 file:// 路径的图片（浏览器无法访问本地文件）
      // 注意：如果 handlePaste 成功提取了图片数据，这里不会执行（因为图片已被替换）
      cleaned = cleaned.replace(/<img[^>]*src=["']file:\/\/[^"']+["'][^>]*>/gi, (match) => {
        // 可以在这里添加提示，但为了不影响粘贴，先静默移除
        return ''
      })
      
      // 确保图片标签完整（Word 可能生成不完整的 img）
      cleaned = cleaned.replace(/<img([^>]*?)(?:\s*\/)?>/gi, (match, attrs) => {
        // 如果图片没有 src，尝试从 data 属性获取
        if (!attrs.includes('src=')) {
          const dataMatch = attrs.match(/data:image\/[^;]+;base64,[^"'\s]+/i)
          if (dataMatch) {
            return `<img src="${dataMatch[0]}" ${attrs} />`
          }
        }
        return match
      })
      
      return cleaned
    },
    handlePaste(view, event, slice) {
      const clipboardData = event.clipboardData
      if (!clipboardData || !editor.value) return false
      
      const items = Array.from(clipboardData.items || [])
      
      // 只检查真正的图片二进制数据
      const imageItems = items.filter(item => item.type.startsWith('image/'))
      
      // 只有在确实有图片二进制数据时才拦截处理
      if (imageItems.length > 0) {
        event.preventDefault()
        
        // 提取所有图片并转换为 base64
        const imagePromises = imageItems.map((item, index) => {
          return new Promise((resolve) => {
            try {
              const file = item.getAsFile()
              if (file && file.size > 0) {
                const reader = new FileReader()
                reader.onload = (e) => {
                  resolve({ index, base64: e.target.result })
                }
                reader.onerror = () => resolve(null)
                reader.readAsDataURL(file)
              } else {
                resolve(null)
              }
            } catch (err) {
              resolve(null)
            }
          })
        })
        
        Promise.all(imagePromises).then(images => {
          const validImages = images.filter(Boolean).sort((a, b) => (a.index || 0) - (b.index || 0))
          const htmlData = clipboardData.getData('text/html')
          
          if (htmlData) {
            // 有 HTML：替换 file:// 图片为 base64
            let imageIndex = 0
            let processedHtml = htmlData.replace(/<img([^>]*?)src=["']file:\/\/[^"']+["']([^>]*?)>/gi, (match, before, after) => {
              if (imageIndex < validImages.length) {
                const base64 = validImages[imageIndex].base64
                imageIndex++
                const cleanBefore = before.replace(/\s*contenteditable=["'][^"']*["']/gi, '')
                const cleanAfter = after.replace(/\s*contenteditable=["'][^"']*["']/gi, '')
                return `<img${cleanBefore}src="${base64}"${cleanAfter}>`
              }
              return ''
            })
            editor.value.chain().focus().insertContent(processedHtml).run()
          } else {
            // 没有 HTML，直接插入图片
            validImages.forEach(img => {
              editor.value.chain().focus().setImage({ src: img.base64 }).run()
            })
          }
        }).catch(() => {
          // 失败时回退：插入纯文本
          const textData = clipboardData.getData('text/plain')
          if (textData && editor.value) {
            editor.value.chain().focus().insertContent(textData).run()
          }
        })
        
        return true
      }
      
      // 没有图片二进制数据，让默认粘贴行为继续
      // transformPastedHTML 会处理格式并移除 file:// 图片
      return false
    },
  },
  onUpdate({ editor: ed }) {
    const html = ed.getHTML()
    emit('update:modelValue', html)
    emit('change', html)
  },
})

// 父组件更新 modelValue 时同步到编辑器（避免光标跳转，只在内容真正不同时更新）
watch(() => props.modelValue, (val) => {
  if (!editor.value) return
  const current = editor.value.getHTML()
  if (val !== current) {
    editor.value.commands.setContent(val || '<p></p>', false)
  }
})

// 工具栏按钮定义
const toolbarButtons = computed(() => {
  if (!editor.value) return []
  const e = editor.value
  return [
    {
      action: 'bold', title: '加粗',
      icon: '<b>B</b>',
      isActive: () => e.isActive('bold'),
      command: () => e.chain().focus().toggleBold().run(),
    },
    {
      action: 'italic', title: '斜体',
      icon: '<i>I</i>',
      isActive: () => e.isActive('italic'),
      command: () => e.chain().focus().toggleItalic().run(),
    },
    {
      action: 'underline', title: '下划线',
      icon: '<u>U</u>',
      isActive: () => e.isActive('underline'),
      command: () => e.chain().focus().toggleUnderline().run(),
    },
    {
      action: 'strike', title: '删除线',
      icon: '<s>S</s>',
      isActive: () => e.isActive('strike'),
      command: () => e.chain().focus().toggleStrike().run(),
    },
    {
      action: 'cleanImages', title: '清理装饰图片（删除小于100px的图片）',
      icon: '🧹',
      command: () => {
        if (!confirm('将删除所有宽度或高度小于100px的图片（通常是装饰性图片），确定吗？')) return
        
        const { state, view } = e
        const { tr } = state
        let modified = false
        
        state.doc.descendants((node, pos) => {
          if (node.type.name === 'image') {
            const img = new window.Image()
            img.src = node.attrs.src
            img.onload = () => {
              if (img.width < 100 || img.height < 100) {
                // 删除小图片
                const deletePos = pos
                const deleteSize = node.nodeSize
                tr.delete(deletePos, deletePos + deleteSize)
                modified = true
              }
            }
          }
        })
        
        if (modified) {
          view.dispatch(tr)
          setTimeout(() => {
            alert('装饰图片已清理')
          }, 500)
        } else {
          alert('未发现需要清理的小图片')
        }
      },
    },
    { action: 'sep1', title: '', icon: '', command: () => {} },
    {
      action: 'h1', title: '标题1',
      icon: 'H1',
      isActive: () => e.isActive('heading', { level: 1 }),
      command: () => e.chain().focus().toggleHeading({ level: 1 }).run(),
    },
    {
      action: 'h2', title: '标题2',
      icon: 'H2',
      isActive: () => e.isActive('heading', { level: 2 }),
      command: () => e.chain().focus().toggleHeading({ level: 2 }).run(),
    },
    {
      action: 'h3', title: '标题3',
      icon: 'H3',
      isActive: () => e.isActive('heading', { level: 3 }),
      command: () => e.chain().focus().toggleHeading({ level: 3 }).run(),
    },
    { action: 'sep2', title: '', icon: '', command: () => {} },
    {
      action: 'bulletList', title: '无序列表',
      icon: '&#8226;',
      isActive: () => e.isActive('bulletList'),
      command: () => e.chain().focus().toggleBulletList().run(),
    },
    {
      action: 'orderedList', title: '有序列表',
      icon: '1.',
      isActive: () => e.isActive('orderedList'),
      command: () => e.chain().focus().toggleOrderedList().run(),
    },
    { action: 'sep3', title: '', icon: '', command: () => {} },
    {
      action: 'alignLeft', title: '左对齐',
      icon: '&#8676;',
      isActive: () => e.isActive({ textAlign: 'left' }),
      command: () => e.chain().focus().setTextAlign('left').run(),
    },
    {
      action: 'alignCenter', title: '居中',
      icon: '&#8596;',
      isActive: () => e.isActive({ textAlign: 'center' }),
      command: () => e.chain().focus().setTextAlign('center').run(),
    },
    {
      action: 'alignRight', title: '右对齐',
      icon: '&#8677;',
      isActive: () => e.isActive({ textAlign: 'right' }),
      command: () => e.chain().focus().setTextAlign('right').run(),
    },
    { action: 'sep4', title: '', icon: '', command: () => {} },
    {
      action: 'blockquote', title: '引用',
      icon: '&#8220;',
      isActive: () => e.isActive('blockquote'),
      command: () => e.chain().focus().toggleBlockquote().run(),
    },
    {
      action: 'code', title: '代码',
      icon: '&lt;/&gt;',
      isActive: () => e.isActive('codeBlock'),
      command: () => e.chain().focus().toggleCodeBlock().run(),
    },
    {
      action: 'hr', title: '分割线',
      icon: '&#8212;',
      command: () => e.chain().focus().setHorizontalRule().run(),
    },
    { action: 'sep5', title: '', icon: '', command: () => {} },
    {
      action: 'undo', title: '撤销',
      icon: '&#8617;',
      command: () => e.chain().focus().undo().run(),
    },
    {
      action: 'redo', title: '重做',
      icon: '&#8618;',
      command: () => e.chain().focus().redo().run(),
    },
  ]
})

// 提供给父组件的方法：获取/设置内容
const getHTML = () => editor.value?.getHTML() || ''
const setHTML = (html) => {
  editor.value?.commands.setContent(html || '<p></p>', false)
}

defineExpose({ getHTML, setHTML, editor })
</script>

<style scoped>
.tiptap-editor-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
  background: #fff;
}

/* 工具栏 */
.tiptap-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
  padding: 6px 8px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
  flex-shrink: 0;
}

.tb-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  padding: 0 5px;
  border: none;
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  transition: all 0.15s;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.tb-btn:hover {
  background: #e6e8eb;
  color: #303133;
}

.tb-btn.active {
  background: #409eff;
  color: #fff;
}

/* 分隔符 */
.tb-btn[title=""] {
  width: 1px;
  min-width: 1px;
  height: 18px;
  padding: 0;
  margin: 0 4px;
  background: #dcdfe6;
  cursor: default;
  pointer-events: none;
}

/* 编辑内容区 */
.tiptap-content-wrap {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.tiptap-content {
  height: 100%;
}

/* Tiptap 编辑器核心样式 */
.tiptap-content :deep(.tiptap) {
  min-height: 100%;
  padding: 12px 16px;
  outline: none;
  font-family: -apple-system-font, BlinkMacSystemFont, "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 16px;
  line-height: 1.75;
  color: #1e1e1e;
}

.tiptap-content :deep(.tiptap p) {
  margin: 0 0 0.8em 0;
}

.tiptap-content :deep(.tiptap h1) {
  font-size: 24px;
  font-weight: 700;
  margin: 0.6em 0 0.4em;
}

.tiptap-content :deep(.tiptap h2) {
  font-size: 20px;
  font-weight: 700;
  margin: 0.5em 0 0.3em;
}

.tiptap-content :deep(.tiptap h3) {
  font-size: 18px;
  font-weight: 600;
  margin: 0.4em 0 0.3em;
}

.tiptap-content :deep(.tiptap img) {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0.5em 0;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

/* 图片选中状态 */
.tiptap-content :deep(.tiptap img.ProseMirror-selectednode) {
  outline: 3px solid #409eff;
  outline-offset: 2px;
  box-shadow: 0 0 0 1px #409eff;
}

/* 图片悬停状态 */
.tiptap-content :deep(.tiptap img:hover) {
  opacity: 0.9;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* 视频样式 */
.tiptap-content :deep(.tiptap video) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 1em 0;
  display: block;
}

.tiptap-content :deep(.tiptap video:focus) {
  outline: 2px solid #409eff;
  outline-offset: 2px;
}

.tiptap-content :deep(.tiptap blockquote) {
  border-left: 4px solid #409eff;
  margin: 0.8em 0;
  padding: 0.5em 1em;
  color: #606266;
  background: #f5f7fa;
  border-radius: 0 4px 4px 0;
}

.tiptap-content :deep(.tiptap ul),
.tiptap-content :deep(.tiptap ol) {
  padding-left: 1.5em;
  margin: 0.5em 0;
}

.tiptap-content :deep(.tiptap hr) {
  border: none;
  border-top: 2px solid #e4e7ed;
  margin: 1em 0;
}

.tiptap-content :deep(.tiptap pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px 16px;
  border-radius: 6px;
  font-family: "Fira Code", "Consolas", monospace;
  font-size: 14px;
  overflow-x: auto;
}

.tiptap-content :deep(.tiptap a) {
  color: #409eff;
  text-decoration: underline;
}

.tiptap-content :deep(.tiptap .ProseMirror-focused) {
  outline: none;
}
</style>
