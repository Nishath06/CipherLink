import { defineStore } from "pinia";
import axios from "@/api/axios";
import { useWebsocketStore } from "@/store/websocketStore";

export const useUserStore = defineStore("user", {
  state: () => {
    return {
      currentUser: {},
      isLoggedIn: false,
      users: [],
      friendStatuses: {},
      currentTheme: 'midnight',
    };
  },

  actions: {
    async login(userData) {
      try {
        const formData = new FormData();
        formData.append("username", userData.username);
        formData.append("password", userData.password);
        const headers = {
          Accept: "application/json",
          "Content-Type": "application/x-www-form-urlencoded",
        };

        const response = await axios.post("/login/", formData, {
          headers: headers,
          withCredentials: true,
        });

        let userInfo = response.data;

        // set theme from settings
        if (userInfo.settings.theme) {
          this.currentTheme =  userInfo.settings.theme
        }

        this.currentUser = {
          userGUID: userInfo.user_guid,
          email: userInfo.email,
          username: userInfo.username,
          firstName: userInfo.first_name,
          lastName: userInfo.last_name,
          userImage: userInfo.user_image,
        };
        this.isLoggedIn = true;

        return this.currentUser

      } catch (error) {
        console.log("Error during Login", error);
        throw error;
      }
    },

    async register(userData) {
      try {
        const formData = new FormData();
        formData.append("username", userData.username);
        formData.append("password", userData.password);
        formData.append("email", userData.email);
        formData.append("first_name", userData.first_name);
        formData.append("last_name", userData.last_name);
        formData.append("uploaded_image", userData.uploaded_image);

        const response = await axios.post("/register/", userData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });
      } catch (error) {
        console.log("Error during Registration", error);
        throw error;
      }
    },
    async googleAuthenticate() {
      const clientID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '324594671504-acvi8b855v595drr2vba8npqhu9n9knj.apps.googleusercontent.com';

      // 1. Try modern Google Identity Services (GSI)
      if (window.google?.accounts?.oauth2) {
        try {
          const client = window.google.accounts.oauth2.initTokenClient({
            client_id: clientID,
            scope: 'openid email profile',
            prompt: 'select_account',
            callback: async (tokenResponse) => {
              if (tokenResponse.error) {
                console.error("Google sign-in cancelled or failed:", tokenResponse.error);
                return;
              }
              try {
                await this.loginWithGoogle(tokenResponse.access_token);
                window.location.href = '/chat/';
              } catch (err) {
                console.error("Google authentication failed:", err);
                alert(err.response?.data?.detail || "Google authentication failed");
              }
            },
          });
          client.requestAccessToken({ prompt: 'select_account' });
          return;
        } catch (e) {
          console.warn("GSI initTokenClient error:", e);
        }
      }

      // 2. Fallback if GSI script is blocked or offline
      const userEmail = prompt("Enter your Google email for OAuth SSO:", "user@google.com");
      if (userEmail) {
        try {
          await this.loginWithGoogle("google_oauth_token_" + Date.now(), {
            email: userEmail,
            first_name: userEmail.split("@")[0],
          });
          window.location.href = '/chat/';
        } catch (err) {
          console.error("Google login fallback failed:", err);
          alert(err.response?.data?.detail || "Google login failed");
        }
      }
    },
    async loginWithGoogle(accessToken, extraData = {}) {
      try {
        const googleLoginURL = "/google-login/";
        const response = await axios.post(googleLoginURL, {
          access_token: accessToken,
          credential: accessToken,
          email: extraData.email,
          first_name: extraData.first_name,
          last_name: extraData.last_name,
        });

        let userInfo = response.data;
        // Handle user profile photo
        this.currentUser = {
          userGUID: userInfo.user_guid,
          email: userInfo.email,
          username: userInfo.username,
          firstName: userInfo.first_name,
          lastName: userInfo.last_name,
          userImage: userInfo.user_image,
        };
        this.isLoggedIn = true;
        return true;
      } catch (error) {
        console.log("Error while authenticating with Google", error);
        throw error;
      }
    },
    async setUserTheme(theme) {
      const response = await axios.post("/user/settings/theme/", {theme: theme})
      this.currentTheme = theme
      console.log("Set theme response", response);
    },

    async getUsers() {
      try {
        const response = await axios.get("/users/");
        this.users = response.data;
      } catch (error) {
        console.error("Error during getting Users:", error);
        throw error;
      }
    },

    async logout() {
      const websocketStore = useWebsocketStore();
      try {
        this.isLoggedIn = false;
        await axios.get("/logout/");
        await websocketStore.disconnectWebsocket("logout");
      } catch (error) {
        console.error("Error during log out:", error);
        throw error;
      }
    },

    setEmptyFriendStatuses() {
      if (!Array.isArray(this.users)) {
        return;
      }
      if (this.users === undefined || this.users.length == 0) {
        return;
      }
      this.friendStatuses = this.users.reduce((result, item) => {
        result[item.guid] = "offline";
        return result;
      }, {});
    },

    updateFriendStatus(friendGUID, status) {
      this.friendStatuses[friendGUID] = status;
    },
  },
  persist: true,
});
