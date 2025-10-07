// const API_BASE =
//   window.location.hostname === "localhost" ? "http://127.0.0.1:8000" : "/api";

// Better API_BASE detection
const API_BASE = (() => {
  const hostname = window.location.hostname;
  const protocol = window.location.protocol;

  // If opened as file:// or localhost, use local server
  if (
    protocol === "file:" ||
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === ""
  ) {
    return "http://127.0.0.1:8000";
  }
  // Otherwise use /api for production
  return ""; // CHANGE: The root path is correct, not /api
})();

console.log("API_BASE set to:", API_BASE);

document.getElementById("showSignup").addEventListener("click", (e) => {
  e.preventDefault();
  document.getElementById("loginForm").classList.add("hidden");
  document.getElementById("signupForm").classList.remove("hidden");
});

document.getElementById("showLogin").addEventListener("click", (e) => {
  e.preventDefault();
  document.getElementById("signupForm").classList.add("hidden");
  document.getElementById("loginForm").classList.remove("hidden");
});

document.getElementById("loginBtn").addEventListener("click", async () => {
  const username = document.getElementById("loginUsername").value;
  const password = document.getElementById("loginPassword").value;

  try {
    // CHANGE: Call the correct endpoint directly
    const response = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json();

    if (response.ok) {
      localStorage.setItem("user", JSON.stringify(data));
      window.location.href = "challenge.html";
    } else {
      alert("Login failed: " + data.detail);
    }
  } catch (error) {
    alert("Login error: " + error.message);
  }
});

document.getElementById("signupBtn").addEventListener("click", async () => {
  const username = document.getElementById("signupUsername").value;
  const email = document.getElementById("signupEmail").value;
  const password = document.getElementById("signupPassword").value;

  console.log("Attempting signup with:", { username, email }); // Add this
  console.log("API_BASE:", API_BASE); // Add this

  // Validate password length
  if (password.length > 72) {
    alert("Password must be 72 characters or less");
    return;
  }

  try {
    // CHANGE: Call the correct endpoint directly
    const response = await fetch(`${API_BASE}/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });

    const data = await response.json();

    if (response.ok) {
      alert("Signup successful! Please login.");
      document.getElementById("showLogin").click();
    } else {
      alert("Signup failed: " + data.detail);
    }
  } catch (error) {
    alert("Signup error: " + error.message);
  }
});