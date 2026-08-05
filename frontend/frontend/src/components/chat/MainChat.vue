<template>
  <MessagesLoading v-if="loadingMessages" :style="compactView ? { 'height': '450px' } : { 'height': '550px' }" />
  <v-card v-show="!loadingMessages" class="rounded-0">
    <div id="container" ref="chatWindow" :style="compactView ? { 'height': '450px' } : { 'height': '550px' }">
      <div v-for="(message, index) in currentChatMessages" :key="message.message_guid">
        <div v-show="showDateBreak(index)" class="text-center text-black my-2 font-weight-medium">
          {{ formatDate(message.created_at) }}
          <v-divider class="mt-2 mx-auto border-opacity-75" width="200px" color="primary" thickness="2px"></v-divider>
        </div>

        <div v-show="earliestUnreadMessageIndex === index" class="bg-items text-center py-2">
          <p class="text-primary font-weight-medium">Unread messages</p>
        </div>

        <!-- ✅ Speaker Bubble (Sender) -->
        <!-- ✅ Speaker Bubble (Sender) -->
        <SpeakerBubble v-if="message.user_guid === currentUser.userGUID" class="ml-auto mr-2">
          <v-list-item class="py-2 my-3 text-right">
            <v-list-item-title class="text-wrap">
              <template v-if="!message.type || message.type === 'new'">
                {{ message.content }}
              </template>
              <template v-else-if="message.type === 'new_file' || message.message_type === 'file'">
                <template v-if="message.isImage">

                  <v-img v-if="message.file_url" :src="message.file_url" class="rounded-lg" max-height="200" max-width="200" contain />
                  <v-btn v-if="message.file_url" :href="message.file_s3url" target="_blank" download color="black" variant="outlined">
                    Download {{ message.content }}
                  </v-btn>
                  <p v-else class="text-red">Image URL missing</p>
                </template>

                <template v-else-if="message.type === 'new_file' || message.message_type === 'file'">
                  <!-- Debugging: Print file_url -->
                  <v-btn v-if="message.file_s3url" :href="message.file_s3url" target="_blank" download color="black" variant="outlined">
                    Download {{ message.content }}
                  </v-btn>
                  <p v-else class="text-red">File URL missing</p>
                </template>

              </template>
            </v-list-item-title>
            <v-list-item-subtitle class="mt-1">
              {{ formatTimestamp(message.created_at) }}
              <v-icon v-if="message.is_sending" class="text-gray">mdi-check</v-icon>
              <v-icon v-else :class="message.is_read ? 'text-blue' : 'text-gray'">mdi-check-all</v-icon>
            </v-list-item-subtitle>
          </v-list-item>
        </SpeakerBubble>

        <!-- ✅ Partner Bubble (Receiver) -->
        <PartnerBubble v-else style="scroll-margin: 50px;" class="ml-2 partner-msg" :id="message.message_guid"
          :index="index">
          <v-list-item class="py-2 my-3 ml-2 text-left">
            <v-list-item-title class="text-wrap">
              <template v-if="!message.type || message.type === 'new'">
                {{ message.content }}
              </template>
              <template v-else-if="message.type === 'new_file' || message.message_type === 'file'">
                <template v-if="message.isImage">

                  <v-img v-if="message.file_url" :src="message.file_url" class="rounded-lg" max-height="200" max-width="200" contain />
                  <v-btn v-if="message.file_url" :href="message.file_s3url" target="_blank" download color="black" variant="outlined">
                    Download {{ message.content }}
                  </v-btn>
                  <p v-else class="text-red">Image URL missing</p>
                </template>

                <template v-else-if="message.type === 'new_file' || message.message_type === 'file'">
                  <p>{{ message.file_url }}</p> <!-- Debugging: Print file_url -->
                  <v-btn v-if="message.file_s3url" :href="message.file_s3url" target="_blank" download color="black" variant="outlined">
                    Download {{ message.content }}
                  </v-btn>
                  <p v-else class="text-red">File URL missing</p>
                </template>

              </template>
            </v-list-item-title>

            <v-list-item-subtitle class="mt-2">
              {{ formatTimestamp(message.created_at) }}
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
  if (index === messages.length - 1) return true;
  const currentDate = new Date(messages[index].created_at).toDateString();
  const nextDate = new Date(messages[index + 1].created_at).toDateString();
  return currentDate !== nextDate;
};
const loadMoreMessages = async () => {
  try {
    const lastMessageGUID = currentChatMessages.value[currentChatMessages.value.length - 1]["message_guid"];
    const getHistoricalMessagesResponse = await messageStore.getHistoricalMessages(currentChatGUID.value, lastMessageGUID);
    const oldMessages = getHistoricalMessagesResponse.messages;
    oldMessages.forEach((oldMessage) => {
      currentChatMessages.value.push(oldMessage);
    });
    moreMessagesToLoad.value = getHistoricalMessagesResponse.has_more_messages;
  } catch (error) {
    console.error("Error fetching chat history:", error);
  }
};

// const loadMoreMessages = async () => {
//   try {
//     console.log("Attempting to load more messages...");

//     if (!moreMessagesToLoad.value) {
//       console.warn("No more messages to load.");
//       return;
//     }

//     if (currentChatMessages.value.length === 0) {
//       console.warn("No messages available to load older messages.");
//       return;
//     }

//     const lastMessageGUID = currentChatMessages.value.at(-1)?.message_guid;
//     if (!lastMessageGUID) {
//       console.warn("Last message GUID is missing.");
//       return;
//     }

//     console.log(`Fetching older messages for chat: ${currentChatGUID.value}, last message: ${lastMessageGUID}`);

//     const getHistoricalMessagesResponse = await messageStore.getHistoricalMessages(
//       currentChatGUID.value,
//       lastMessageGUID
//     );

//     if (!getHistoricalMessagesResponse || !getHistoricalMessagesResponse.messages) {
//       console.warn("Invalid response received from API.");
//       return;
//     }

//     console.log("API Response:", getHistoricalMessagesResponse);

//     let oldMessages = getHistoricalMessagesResponse.messages.map((message) => {
//       console.log("Processing message:", message);

//       if (message.message_type === "file") {
//         console.log(`File message - Name: ${message.file_name}, URL: ${message.file_url}, Extension: ${message.file_extension}`);

//         // Determine if the file is an image
//         const imageExtensions = ["jpg", "jpeg", "png", "gif", "bmp", "webp"];
//         const isImage = imageExtensions.includes(message.file_extension?.toLowerCase());
//         console.log("File message detected - GUID:", message.message_guid, "file_url:", message.file_url, "file_path:", message.file_path);

//         return {
//           ...message,
//           file_url: message.file_url, // Ensure valid file URL
//           file_extension: message.file_extension ? message.file_extension.toLowerCase() : "", // Ensure valid file extension
//           isImage, // Set the isImage flag
//         };
//       }

//       return message; // Return text messages unchanged
//     });

//     // Prepend messages using reactive update
//     console.log("Adding messages to the chat:", oldMessages);
//     currentChatMessages.value = [...oldMessages, ...currentChatMessages.value];

//     // Ensure `has_more_messages` is a boolean
//     moreMessagesToLoad.value = !!getHistoricalMessagesResponse.has_more_messages;
//     console.log("More messages available:", moreMessagesToLoad.value);
//   } catch (error) {
//     console.error("Error fetching chat history:", error);
//   }
// };


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
</style>
