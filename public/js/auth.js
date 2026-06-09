(function () {
  function setAuthenticated(user) {
    App.state.currentUser = user;
    App.state.email = user.email || App.state.email || "";
    if (user.email) localStorage.setItem("opsAgentEmail", user.email);
    $("authUserBox").hidden = false;
    $("authUserLabel").textContent = user.email;
    document.querySelector(".nav-tabs").hidden = false;
  }

  function showLogin() {
    App.state.currentUser = null;
    $("authUserBox").hidden = true;
    document.querySelector(".nav-tabs").hidden = true;
    switchView("login");
  }

  async function loadStatus() {
    try {
      const data = await request("/auth/status");
      return Boolean(data.enabled);
    } catch (_) {
      return true;
    }
  }

  function disableAuthUi() {
    App.state.currentUser = null;
    $("authUserBox").hidden = true;
    document.querySelector(".nav-tabs").hidden = false;
  }

  async function loadCurrentUser() {
    try {
      const data = await request("/auth/me");
      setAuthenticated(data.user);
      return data.user;
    } catch (_) {
      showLogin();
      return null;
    }
  }

  async function login(event) {
    event.preventDefault();
    const button = $("loginBtn");
    button.disabled = true;
    button.textContent = "登入中...";
    try {
      const data = await request("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: $("loginEmail").value.trim(),
          password: $("loginPassword").value,
        }),
      });
      $("loginPassword").value = "";
      setAuthenticated(data.user);
      showToast("登入成功。");
      await window.loadAppData();
    } catch (err) {
      showToast(`登入失敗：${err.message}`);
    } finally {
      button.disabled = false;
      button.textContent = "登入";
    }
  }

  async function logout() {
    try {
      await request("/auth/logout", { method: "POST" });
    } catch (_) {
      // Even if the session is already gone, the local UI should return to login.
    }
    showLogin();
    showToast("已登出。");
  }

  window.Auth = {
    loadStatus,
    loadCurrentUser,
    login,
    logout,
    showLogin,
    setAuthenticated,
    disableAuthUi,
  };
}());
