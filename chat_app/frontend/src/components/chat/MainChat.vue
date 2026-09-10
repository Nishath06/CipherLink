<template>
  <MessagesLoading v-if="loadingMessages" :style="compactView ? { 'height': '450px' } : { 'height': '550px' }" />
  <v-card v-show="!loadingMessages" class="rounded-0">
    <div id="container" ref="chatWindow" :style="compactView ? { 'height': '450px' } : { 'height': '550px' }">
      <div v-for="(message, index) in currentChatMessages" :key="message.message_guid || message.temp_id || index">
        <div v-show="showDateBreak(index)" class="text-center text-black my-2 font-weight-medium">
          {{ formatDate(message.created_at) }}
          <v-divider class="mt-2 mx-auto border-opacity-75" width="200px" color="primary" thickness="2px"></v-divider>
        </div>

        <div v-show="earliestUnreadMessageIndex === index" class="bg-items text-center py-2 my-1">
          <p class="text-primary font-weight-medium">Unread messages</p>
        </div>

        <!-- ✅ Speaker Bubble (Sender) -->
        <SpeakerBubble
          v-if="String(message.user_guid).toLowerCase() === String(currentUser.userGUID).toLowerCase()"
          class="ml-auto mr-2"
        >
          <v-list-item class="py-1 px-3 my-2 text-right">
            <v-list-item-title class="text-wrap">
              <template v-if="message.type === 'new_file' || message.message_type === 'file'">
                <template v-if="message.isImage">
                  <v-img
                    v-if="message.file_url"
                    :src="message.file_url"
                    class="rounded-lg mb-2 ml-auto"
                    max-height="240"
                    max-width="260"
                    contain
                  />
                  <v-btn
                    v-if="message.file_url || message.file_s3url"
                    :href="message.file_url || message.file_s3url"
                    target="_blank"
                    :download="message.file_name || 'image'"
                    color="primary"
                    variant="tonal"
                    size="small"
                    class="text-none"
                  >
                    <v-icon start>mdi-download</v-icon> {{ message.file_name || 'Download Image' }}
                  </v-btn>
                  <p v-else class="text-red">Image URL missing</p>
                </template>

                <template v-else>
                  <v-btn
                    v-if="message.file_url || message.file_s3url"
                    :href="message.file_url || message.file_s3url"
                    target="_blank"
                    :download="message.file_name || 'file'"
                    color="primary"
                    variant="tonal"
                    size="small"
                    class="text-none"
                  >
                    <v-icon start>mdi-paperclip</v-icon> {{ message.file_name || 'Download File' }}
                  </v-btn>
                  <p v-else class="text-red">File URL missing</p>
                </template>
              </template>
              <template v-else>
                <div class="message-text">{{ message.content }}</div>
              </template>
            </v-list-item-title>
            <v-list-item-subtitle class="mt-1 d-flex align-center justify-end">
              <span class="mr-1">{{ formatTimestamp(message.created_at) }}</span>
              <v-icon v-if="message.is_sending" size="small" color="grey">mdi-check</v-icon>
              <v-icon v-else size="small" :color="message.is_read ? 'blue' : 'grey'">mdi-check-all</v-icon>
            </v-list-item-subtitle>
          </v-list-item>
        </SpeakerBubble>

        <!-- ✅ Partner Bubble (Receiver) -->
        <PartnerBubble
          v-else
          style="scroll-margin: 50px;"
          class="mr-auto ml-2 partner-msg"
          :id="message.message_guid"
          :index="index"
        >
          <v-list-item class="py-1 px-3 my-2 text-left">
            <v-list-item-title class="text-wrap">
              <template v-if="message.type === 'new_file' || message.message_type === 'file'">
                <template v-if="message.isImage">
                  <v-img
                    v-if="message.file_url"
                    :src="message.file_url"
                    class="rounded-lg mb-2"
                    max-height="240"
                    max-width="260"
                    contain
                  />
                  <v-btn
                    v-if="message.file_url || message.file_s3url"
                    :href="message.file_url || message.file_s3url"
                    target="_blank"
                    :download="message.file_name || 'image'"
                    color="primary"
                    variant="tonal"
                    size="small"
                    class="text-none"
                  >
                    <v-icon start>mdi-download</v-icon> {{ message.file_name || 'Download Image' }}
                  </v-btn>
                  <p v-else class="text-red">Image URL missing</p>
                </template>

                <template v-else>
                  <v-btn
                    v-if="message.file_url || message.file_s3url"
                    :href="message.file_url || message.file_s3url"
                    target="_blank"
                    :download="message.file_name || 'file'"
                    color="primary"
                    variant="tonal"
                    size="small"
                    class="text-none"
                  >
                    <v-icon start>mdi-paperclip</v-icon> {{ message.file_name || 'Download File' }}
                  </v-btn>
                  <p v-else class="text-red">File URL missing</p>
                </template>
              </template>
              <template v-else>
                <div class="message-text">{{ message.content }}</div>
              </template>
            </v-list-item-title>

            <v-list-item-subtitle class="mt-1 d-flex align-center justify-start">
              <span>{{ formatTimestamp(message.created_at) }}</span>
            </v-list-item-subtitle>
          </v-list-item>
        </PartnerBubble>
      </div>

      <v-btn v-if="moreMessagesToLoad" @click="loadMoreMessages" class="mt-3 mx-auto" style="text-transform: none">
        Load More
      </v-btn>
    </div>

    <!-- Scroll to bottom button -->
    <div style="position: absolute;" :style="compactView ? {top: '85%', right: '7%'} : {top: '88%', right: '5%'}">
      <p v-if="!isBottom && chatStore.getUnreadMessagesforChat(currentChatGUID)"
        style="text-align: center; color: rgb(var(--v-theme-scroll)); font-size: 12px; font-weight: bolder;">
        {{ chatStore.getUnreadMessagesforChat(currentChatGUID) }}
      </p>
      <v-btn v-show="!isBottom" icon class="rounded-circle" @click="chatStore.scrollToBottom('smooth')"
        style="width: 35px; height: 35px;">
        <v-icon size="x-large" color="scroll">mdi-chevron-down</v-icon>
      </v-btn>
    </div>
  </v-card>
</template>

<script setup>
import { onMounted, ref } from "vue";
import PartnerBubble from "@/components/chat/PartnerBubble.vue";
import SpeakerBubble from "@/components/chat/SpeakerBubble.vue";
import MessagesLoading from "@/components/chat/MessagesLoading.vue";

import { storeToRefs } from "pinia";
import { useUserStore } from "@/store/userStore";
import { useChatStore } from "@/store/chatStore";
import { useMessageStore } from "@/store/messageStore";
import { useObserverStore } from "@/store/observerStore";
import { useMainStore } from "@/store/mainStore";

import { formatTimestamp, formatDate } from "@/utils/dateUtils";

const userStore = useUserStore();
const chatStore = useChatStore();
const messageStore = useMessageStore();
const observerStore = useObserverStore();
const mainStore = useMainStore();
const { compactView } = storeToRefs(mainStore);

const { currentUser } = storeToRefs(userStore);
const { currentChatGUID, isBottom } = storeToRefs(chatStore);
const { currentChatMessages, moreMessagesToLoad, earliestUnreadMessageIndex, loadingMessages } = storeToRefs(messageStore);

const chatWindow = ref(null);

const showDateBreak = (index) => {
  const messages = currentChatMessages.value;
  if (!messages || messages.length === 0) return false;
  if (index === messages.length - 1) return true;
  if (!messages[index]?.created_at || !messages[index + 1]?.created_at) return false;
  const currentDate = new Date(messages[index].created_at).toDateString();
  const nextDate = new Date(messages[index + 1].created_at).toDateString();
  return currentDate !== nextDate;
};

const loadMoreMessages = async () => {
  try {
    if (!currentChatMessages.value || currentChatMessages.value.length === 0) return;
    const lastMessage = currentChatMessages.value[currentChatMessages.value.length - 1];
    if (!lastMessage || !lastMessage.message_guid) return;

    const getHistoricalMessagesResponse = await messageStore.getHistoricalMessages(
      currentChatGUID.value,
      lastMessage.message_guid
    );
    const oldMessages = getHistoricalMessagesResponse?.messages;
    if (Array.isArray(oldMessages)) {
      oldMessages.forEach((oldMessage) => {
        currentChatMessages.value.push(oldMessage);
      });
    }
    moreMessagesToLoad.value = Boolean(getHistoricalMessagesResponse?.has_more_messages);
  } catch (error) {
    console.error("Error fetching chat history:", error);
  }
};

onMounted(() => {
  chatStore.removeWindowScrollHandler();
  observerStore.disconnectObserver();
  chatStore.setChatWindow(chatWindow.value);
  chatStore.addWindowScrollHandler();
  observerStore.initializeObserver();
});
</script>

<style scoped>
#container {
  overflow: auto;
  display: flex;
  flex-direction: column-reverse;
}

#container::-webkit-scrollbar {
  width: 19px;
}

#container::-webkit-scrollbar-track {
  background-color: rgb(var(--v-theme-track));
}

#container::-webkit-scrollbar-thumb {
  background-color: rgb(var(--v-theme-scroll));
  border-radius: 6px;
}

.message-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.4;
  font-size: 0.95rem;
}
</style>
