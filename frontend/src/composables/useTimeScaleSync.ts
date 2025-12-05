import { ref } from 'vue'

// 全局时间轴同步锁，防止循环同步
export const isSyncingTimeScale = ref(false)

export function useTimeScaleSync() {
  return {
    isSyncingTimeScale
  }
}
