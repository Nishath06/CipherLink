<template>
  <div ref="messageBubble" class="bubble bubble-bottom-left">
    <slot></slot>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useObserverStore } from "@/store/observerStore";

const observerStore = useObserverStore();
const messageBubble = ref(null);

onMounted(() => {
  if (observerStore.observer) {
    observerStore.observer.observe(messageBubble.value);
  } else {
    console.log("Could not observe, must fix");
  }
});
</script>

<style scoped>
.bubble {
  position: relative;
  line-height: 22px;
  width: fit-content;
  max-width: 82%;
  min-width: 120px;
  background: #f5f5f5;
  border-radius: 18px;
  text-align: left;
  color: #000;
  word-break: break-word;
  overflow-wrap: break-word;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
}

.bubble-bottom-left:before {
  content: "";
  width: 0px;
  height: 0px;
  position: absolute;
  border-left: 20px solid #f5f5f5;
  border-right: 12px solid transparent;
  border-top: 10px solid #f5f5f5;
  border-bottom: 16px solid transparent;
  left: 8px;
  bottom: -8px;
  transform: rotate(10deg);
}
</style>
