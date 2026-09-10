import { defineStore } from "pinia";
import { useMessageStore } from "@/store/messageStore";
import { useChatStore } from "@/store/chatStore";

export const useObserverStore = defineStore("observer", {
  state: () => {
    return {
      observer: null,
    };
  },
  actions: {
    initializeObserver() {
      const chatStore = useChatStore();

      this.observer = new IntersectionObserver(this.onElementObserved, {
        root: chatStore.chatWindow,
        threshold: 0.5,
      });
    },

    disconnectObserver() {
      if (this.observer) {
        this.observer.disconnect();
      }
    },

    async onElementObserved(entries) {
      const messageStore = useMessageStore();
      const chatStore = useChatStore();

      for (const entry of entries) {
        if (!entry.isIntersecting) {
          continue;
        }

        this.observer.unobserve(entry.target);

        const messageGuid = entry.target.id || entry.target.getAttribute("id");
        let message = null;
        if (messageGuid) {
          message = messageStore.currentChatMessages.find((m) => m.message_guid === messageGuid);
        }
        if (!message) {
          const messageIndex = entry.target.getAttribute("index");
          message = messageStore.currentChatMessages[messageIndex];
        }

        if (!message || message.is_read) {
          continue;
        }

        await messageStore.markMessageAsRead(message);

        // find chat and recalculate new messages count
        const foundChatIndex = chatStore.directChats.findIndex(
          (chat) => chat.chat_guid === message.chat_guid
        );

        if (foundChatIndex !== -1) {
          // re-calculate new messages count for observed chat
          chatStore.directChats[foundChatIndex].new_messages_count = messageStore.calculateNewMessagesCountForChat();
          // re-calculate total unread messages count
          chatStore.calculateTotalUnreadMessagesCount();
        }

        // update 'unread messages' tab with some delay
        setTimeout(() => {
          messageStore.setIndexOfEarliestUnreadMessage();
        }, 1500);
      }
    },
  },
});
