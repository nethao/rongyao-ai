import request from './request'

export function getMediaMappings() {
  return request({
    url: '/media-mappings',
    method: 'get'
  })
}

export function updateMediaMapping(mediaType, siteId) {
  return request({
    url: `/media-mappings/${mediaType}`,
    method: 'put',
    data: { site_id: siteId }
  })
}

export function deleteMediaMapping(mediaType) {
  return request({
    url: `/media-mappings/${mediaType}`,
    method: 'delete'
  })
}
