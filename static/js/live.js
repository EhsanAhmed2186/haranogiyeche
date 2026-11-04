/*
 * Live chat updates (no unread-number badges or popups).
 *
 * No WebSockets: every few seconds the page asks the server for the logged-in user's
 * own new items (GET /notifications/poll/). It updates an open chat in place.
 * If you are inside a conversation, a new message from the other person is added to
 * the chat in place. Text from the server is always inserted with textContent.
 */
(function () {
  var root = document.getElementById("liveRoot");
  if (!root) {
    return; // not logged in
  }

  var POLL_MS = 8000; // how often to ask the server

  var pollUrl = root.dataset.pollUrl;
  var lastNotification = parseInt(root.dataset.lastNotification, 10) || 0;
  var lastMessage = parseInt(root.dataset.lastMessage, 10) || 0;

  var chatBox = document.getElementById("chatBox");
  var openConversation = chatBox ? chatBox.dataset.requestId : "";

  var timer = null;
  var failures = 0;

  function appendBubble(message) {
    if (!chatBox) {
      return;
    }
    var empty = chatBox.querySelector(".chat-empty");
    if (empty) {
      empty.remove();
    }
    var row = document.createElement("div");
    row.className = "chat-row theirs";
    var bubble = document.createElement("div");
    bubble.className = "chat-bubble";
    var text = document.createElement("div");
    text.style.whiteSpace = "pre-wrap";
    text.textContent = message.content;
    var meta = document.createElement("div");
    meta.className = "chat-meta";
    meta.textContent = message.time;
    bubble.appendChild(text);
    bubble.appendChild(meta);
    row.appendChild(bubble);
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function handle(data) {
    // Only the chat you are looking at is updated in place. Nothing pops up anywhere.
    (data.messages || []).forEach(function (message) {
      if (openConversation && String(message.request_id) === String(openConversation)) {
        appendBubble(message);
      }
    });

    lastNotification = data.last_notification_id || lastNotification;
    lastMessage = data.last_message_id || lastMessage;
  }

  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(poll, POLL_MS * (1 + failures));
  }

  function poll() {
    if (document.visibilityState === "hidden") {
      schedule(); // do not bother the server while the tab is in the background
      return;
    }
    var query = "?n=" + lastNotification + "&m=" + lastMessage;
    if (openConversation) {
      query += "&open=" + encodeURIComponent(openConversation);
    }
    fetch(pollUrl + query, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.json();
      })
      .then(function (data) {
        failures = 0;
        handle(data);
      })
      .catch(function (error) {
        failures = Math.min(failures + 1, 5); // slow down when the server is unreachable
        if (window.console) {
          console.warn("Live chat updates paused:", error && error.message);
        }
      })
      .then(schedule);
  }

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") {
      clearTimeout(timer);
      poll(); // catch up the moment the tab comes back
    }
  });

  schedule();
})();
