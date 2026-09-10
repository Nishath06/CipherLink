import { defineStore } from "pinia";
import { useChatStore } from "@/store/chatStore";
import { useMessageStore } from "@/store/messageStore";
import { useUserStore } from "@/store/userStore";

export const useWebsocketStore = defineStore("websocket", {
  state: () => {
    return {
      socket: null,
      reconnectAttempted: false,
    };
  },

  actions: {
    async connectWebsocket() {
      let websocketURL = import.meta.env.VITE_WEBSOCKET_URL;
      const messageStore = useMessageStore();

      try {
        this.socket = new WebSocket(websocketURL);

        this.socket.addEventListener("open", () => {
          // display message for reconnection
          if (this.reconnectAttempted) {
            this.reconnectAttempted = false;
            messageStore.displaySystemMessage(
              "success",
              "Websocket connection re-established",
              2000
            );
          }
          console.log("WebSocket connected");
        });

        this.socket.addEventListener("message", (event) => {
          const receivedMessage = JSON.parse(event.data);
          this.handleNewMessage(receivedMessage);
          this.handleFriendTyping(receivedMessage);
          this.handleStatusMessage(receivedMessage);
          this.handleMessageRead(receivedMessage);
          this.handleNewChatCreated(receivedMessage);
          this.handleChatDeletedNotification(receivedMessage);
        });

        this.socket.addEventListener("close", (event) => {
          console.log("WebSocket connection closed.", event);
          if (!this.reconnectAttempted && event.reason !== "User logout") {
            messageStore.displaySystemMessage(
              "error",
              "Websocket disconnected"
            );

            // Attempt to reconnect only once
            // after 1 second
            setTimeout(() => {
              messageStore.displaySystemMessage(
                "success",
                "Reconnecting to websocket"
              );
              this.connectWebsocket(); // Reconnect
              this.reconnectAttempted = true;
            }, 1000);
          } else {
            // nullify socket variable
            this.socket = null;
          }
        });
      } catch (error) {
        console.log("Error during connecting to Websocket", error);
        throw error;
      }
    },

    async disconnectWebsocket(reason) {
      if (this.socket && reason === "logout") {
        this.socket.close(1000, "User logout");
      }
    },

    async sendMessage(message) {
      const chatStore = useChatStore();
      const userStore = useUserStore();
      // Must first create a chat for unassigned chat
      if (chatStore.currentChatGUID === "unassigned") {
        // find friend guid -> cannot assume that it is the first element in array!
        const friendGUID = chatStore.currentFriendGUID;
        const newChat = await chatStore.createDirectChat(friendGUID);
        // find unassigned chat from directChats and update unassigned chat based on new chat data
        const unassignedChat = chatStore.directChats.find(
          (chat) => chat.chat_guid === "unassigned"
        );
        if (unassignedChat) {
          unassignedChat.chat_guid = newChat.guid;
          unassignedChat.created_at = newChat.created_at;
          unassignedChat.updated_at = newChat.updated_at;
          chatStore.currentChatGUID = newChat.guid;
        } else {
          console.log("No unassigned Chat found");
        }
      }
      // Must check that WebSocket connection exists and the message is not empty before calling
      await this.socket.send(
        JSON.stringify({
          type: "new_message",
          user_guid: userStore.currentUser.userGUID,
          chat_guid: chatStore.currentChatGUID,
          content: message,
        })
      );
    },
    

    async sendMessageRead(message) {
      await this.socket.send(
        JSON.stringify({
          type: "message_read",
          chat_guid: message.chat_guid,
          message_guid: message.message_guid,
        })
      );
    },
    async sendChatDeleted(chatGUID) {
      await this.socket.send(
        JSON.stringify({
          type: "chat_deleted",
          chat_guid: chatGUID,
        })
      );
    },

    handleNewMessage(receivedMessage) {
      const chatStore = useChatStore();
      const messageStore = useMessageStore();
      const userStore = useUserStore();

      if (!receivedMessage) return;

      if (receivedMessage.type === "new" || receivedMessage.type === "new_file") {
        chatStore.inputLocked = false;
        const currentUserId = userStore.currentUser?.userGUID ? String(userStore.currentUser.userGUID).toLowerCase() : "";
        const isMessageFromCurrentUser =
          String(receivedMessage.user_guid).toLowerCase() === currentUserId;

        const foundChatIndex = chatStore.directChats.findIndex(
          (directChat) => directChat.chat_guid === receivedMessage.chat_guid
        );

        if (foundChatIndex !== -1) {
          const foundChat = chatStore.directChats[foundChatIndex];
          foundChat.updated_at = receivedMessage.created_at;
          if (!isMessageFromCurrentUser) {
            foundChat.new_messages_count = (foundChat.new_messages_count || 0) + 1;
            chatStore.totalUnreadMessagesCount = (chatStore.totalUnreadMessagesCount || 0) + 1;
            chatStore.friendTyping = false;
          }
          if (foundChatIndex !== 0) {
            chatStore.directChats.splice(foundChatIndex, 1);
            chatStore.directChats.unshift(foundChat);
          }
        }

        // Process message through standardized message normalizer
        const processedMessage = messageStore.processMessage(receivedMessage);

        // Append message to chat if belongs to currently open chat
        if (processedMessage.chat_guid === chatStore.currentChatGUID) {
          if (isMessageFromCurrentUser && processedMessage.type === "new") {
            // Find temporary sending message
            const pendingIndex = messageStore.currentChatMessages.findIndex(
              (m) => m.is_sending && !m.message_guid && String(m.user_guid).toLowerCase() === currentUserId
            );
            if (pendingIndex !== -1) {
              messageStore.currentChatMessages[pendingIndex].is_sending = false;
              messageStore.currentChatMessages[pendingIndex].message_guid = processedMessage.message_guid;
              messageStore.currentChatMessages[pendingIndex].created_at = processedMessage.created_at;
            } else {
              messageStore.currentChatMessages.unshift(processedMessage);
            }
          } else {
            messageStore.currentChatMessages.unshift(processedMessage);
          }

          // Scroll to bottom when new message arrives
          chatStore.scrollToBottom("smooth");
        }
      }
    },
    

    async handleUserTyping() {
      const chatStore = useChatStore();
      const userStore = useUserStore();

      // should not send for not yet created chat
      if (chatStore.currentChatGUID === "unassigned") {
        return;
      }
      // ignore if meTyping, else send message and change meTyping to false after timeout
      if (chatStore.meTyping === false) {
        chatStore.meTyping = true;

        await this.socket.send(
          JSON.stringify({
            type: "user_typing",
            user_guid: userStore.currentUser.userGUID,
            chat_guid: chatStore.currentChatGUID,
          })
        );

        chatStore.timeoutMeTyping();
      }
    },

    async handleFriendTyping(receivedMessage) {
      const chatStore = useChatStore();
      const userStore = useUserStore();
      //
      if (
        receivedMessage.type === "user_typing" &&
        receivedMessage.user_guid !== userStore.currentUser.userGUID &&
        receivedMessage.chat_guid === chatStore.currentChatGUID
      ) {
        // avoid setting friendIsTyping to false if new message was received
        chatStore.stopTimeoutFriendTyping();
        chatStore.friendTyping = true;
        chatStore.timeoutFriendTyping();
      }
    },

    handleStatusMessage(receivedMessage) {
      const userStore = useUserStore();

      if (receivedMessage.type === "status") {
        // ignore own messages
        if (userStore.currentUser.userGUID === receivedMessage.user_guid) {
          return;
        }
        userStore.updateFriendStatus(
          receivedMessage.user_guid,
          receivedMessage.status
        );
      }
    },

    handleMessageRead(receivedMessage) {
      // function is used to update read status of own messages read by another user
      const userStore = useUserStore();
      const messageStore = useMessageStore();
      if (
        receivedMessage.type === "message_read" &&
        receivedMessage.user_guid !== userStore.currentUser.userGUID
      ) {
        messageStore.updateMessagesReadStatus(
          receivedMessage.last_read_message_created_at
        );
      }
    },

    async handleChatDeletedNotification(receivedMessage) {
      // function is used to notify active websocket users in the chat
      // that the chat has been deleted
      if (receivedMessage.type === "chat_deleted") {
        const chatStore = useChatStore();
        const messageStore = useMessageStore();

        await chatStore.deleteDirectChatByGUID(receivedMessage.chat_guid)
        // re-calculate total unread messages count
        chatStore.calculateTotalUnreadMessagesCount();
        // display Chat was deleted message
        messageStore.displaySystemMessage(
          "info",
          `Chat has been deleted by ${receivedMessage.user_name}`,
          3000
        );
        await chatStore.disselectChat(receivedMessage.chat_guid);
      }

    },

    async handleNewChatCreated(receivedMessage) {
      // function is used to add new direct chat initiated by another user
      // while current user still have not refreshed direct chats
      // it also sends back data to backend to subscribe user to chat and add guid/id to chats

      const chatStore = useChatStore();
      const userStore = useUserStore();
      if (receivedMessage.type === "new_chat_created") {
        delete receivedMessage.type;
        // needed to send data backend [add guid/id pair to chats]
        const chatGUID = receivedMessage.chat_guid;
        const chatID = receivedMessage.chat_id;
        delete receivedMessage.chat_id; // remove to not show in frontend
        await this.socket.send(
          JSON.stringify({
            type: "add_user_to_chat",
            chat_id: chatID,
            chat_guid: chatGUID,
          })
        );
        // make friend's status online
        userStore.updateFriendStatus(receivedMessage.friend.guid, "online");
        // add chat
        chatStore.addNewChat(receivedMessage);
      }
    },

    
    async sendFile(file, receiverGuid = null) {
      const chatStore = useChatStore();
      const userStore = useUserStore();
    
      if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
        console.error("WebSocket is not connected.");
        return;
      }
    
      if (chatStore.currentChatGUID === "unassigned") {
        console.error("Cannot send file to an unassigned chat.");
        return;
      }
    
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = async () => {
        const base64File = reader.result.split(",")[1]; // Extract base64 data
    
        // Get the receiver GUID from parameter or current chat
        const receiver_guid = receiverGuid || chatStore.currentFriendGUID;
    
        if (!receiver_guid) {
          console.error("Receiver GUID is missing.");
          return;
        }
    
        const fileMessage = {
          type: "new_file",
          user_guid: userStore.currentUser.userGUID,
          chat_guid: chatStore.currentChatGUID,
          file_name: file.name,
          file_data: base64File,
          receiver_guid: receiver_guid,
        };
    
        try {
          this.socket.send(JSON.stringify(fileMessage));
          console.log("File sent successfully:", file.name, fileMessage);
        } catch (error) {
          console.error("Error sending file:", error);
        }
      };
    
      reader.onerror = (error) => {
        console.error("Error reading file:", error);
      };
    },
    
  },
  getters: {
    socketExists: (state) => state.socket,
  },
});
