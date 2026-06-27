import { ref } from 'vue'

export function usePagination(defaultSize = 20) {
  const page = ref(1)
  const size = ref(defaultSize)
  const total = ref(0)

  function setPage(p: number) { page.value = p }
  function setSize(s: number) { size.value = s; page.value = 1 }
  function setTotal(t: number) { total.value = t }

  return { page, size, total, setPage, setSize, setTotal }
}