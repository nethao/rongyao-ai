import { Node, mergeAttributes } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import VideoComponent from './VideoComponent.vue'

export const Video = Node.create({
  name: 'video',

  group: 'block',

  atom: true,

  addAttributes() {
    return {
      src: {
        default: null,
      },
      controls: {
        default: true,
      },
      width: {
        default: '100%',
      },
    }
  },

  parseHTML() {
    return [
      {
        tag: 'video',
        getAttrs: (dom) => {
          const source = dom.querySelector('source')
          return {
            src: source?.getAttribute('src') || dom.getAttribute('src'),
            controls: dom.hasAttribute('controls'),
            width: dom.getAttribute('width') || '100%',
          }
        },
      },
    ]
  },

  renderHTML({ HTMLAttributes }) {
    const { src, controls, width } = HTMLAttributes
    return [
      'video',
      mergeAttributes({ controls: controls ? '' : null, width }),
      ['source', { src, type: 'video/mp4' }],
    ]
  },

  addNodeView() {
    return VueNodeViewRenderer(VideoComponent)
  },

  addCommands() {
    return {
      setVideo:
        (options) =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
            attrs: options,
          })
        },
    }
  },
})


