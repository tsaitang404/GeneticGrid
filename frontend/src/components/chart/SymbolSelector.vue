<template>
  <select 
    :value="modelValue"
    @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
    class="symbol-select"
  >
    <option v-for="sym in symbols" :key="sym" :value="sym">
      {{ sym }}
    </option>
  </select>
</template>

<script setup lang="ts">
interface Props {
  modelValue: string
  symbols: string[]
}

defineProps<Props>()
defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<style scoped>
.symbol-selector {
  background: #2a2e39;
  color: #d1d4dc;
  border: 1px solid #363a45;
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 14px;
  cursor: pointer;
  outline: none;
}

.symbol-selector:hover {
  background: #363a45;
}
</style>
