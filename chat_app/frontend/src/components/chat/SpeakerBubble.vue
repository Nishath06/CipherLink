<template>
  <div class="bubble bubble-bottom-right">
    <slot></slot>
  </div>
</template>

<script setup></script>

<style scoped>


.bubble {
  position: relative;
  line-height: 22px;
  width: fit-content;
  max-width: 82%;
  min-width: 120px;
  background: #B9F6CA;
  border-radius: 18px;
  text-align: left;
  color: #000;
  word-break: break-word;
  overflow-wrap: break-word;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
}

.bubble-bottom-right:before {
  content: "";
  width: 0px;
  height: 0px;
  position: absolute;
  border-left: 20px solid transparent;
  border-right: 16px solid transparent;
  border-top: 10px solid transparent;
  border-bottom: 16px solid #B9F6CA;
  right: 8px;
  bottom: -8px;
  transform: rotate(-115deg);
}
</style>
