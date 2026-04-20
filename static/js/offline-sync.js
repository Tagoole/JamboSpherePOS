(function () {
  var STORAGE_KEY = "jambopos:offline-actions:v1";
  var syncing = false;

  function hasLocalStorage() {
    try {
      var k = "__jambopos_test__";
      window.localStorage.setItem(k, "1");
      window.localStorage.removeItem(k);
      return true;
    } catch (error) {
      return false;
    }
  }

  function readQueue() {
    if (!hasLocalStorage()) {
      return [];
    }

    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return [];
      }
      var parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function writeQueue(queue) {
    if (!hasLocalStorage()) {
      return;
    }

    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
    updateSyncBanner();
  }

  function enqueue(action) {
    var queue = readQueue();
    queue.push(action);
    writeQueue(queue);
  }

  function getCookie(name) {
    var cookieValue = null;
    if (!document.cookie) {
      return cookieValue;
    }

    var cookies = document.cookie.split(";");
    for (var i = 0; i < cookies.length; i += 1) {
      var cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }

    return cookieValue;
  }

  function formDataToPairs(formData) {
    var pairs = [];
    formData.forEach(function (value, key) {
      pairs.push([key, String(value)]);
    });
    return pairs;
  }

  function pairsToBody(pairs) {
    var body = new URLSearchParams();
    var csrf = getCookie("csrftoken") || "";

    for (var i = 0; i < pairs.length; i += 1) {
      var pair = pairs[i];
      if (pair[0] === "csrfmiddlewaretoken") {
        continue;
      }
      body.append(pair[0], pair[1]);
    }

    if (csrf) {
      body.append("csrfmiddlewaretoken", csrf);
    }

    return body;
  }

  function dispatchSuccessEvents(action) {
    if (window.htmx) {
      if (action.successEvent) {
        window.htmx.trigger(document.body, action.successEvent);
      }

      if (action.scope === "sales") {
        window.htmx.trigger(document.body, "salesChanged");
      }

      if (action.scope === "products") {
        window.htmx.trigger(document.body, "productsChanged");
      }
    }
  }

  function createPendingBadge(label) {
    var text = label ? "Pending sync: " + label : "Pending sync";
    return '<span class="tag tag-pending" style="margin-left: 8px;">' + text + "</span>";
  }

  function optimisticAppendProduct(action) {
    var tbody = document.getElementById("product-table-body");
    if (!tbody) {
      return;
    }

    var name = "";
    var price = "0.00";
    for (var i = 0; i < action.pairs.length; i += 1) {
      var pair = action.pairs[i];
      if (pair[0] === "product_name") {
        name = pair[1];
      }
      if (pair[0] === "product_price") {
        price = pair[1];
      }
    }

    if (!name) {
      return;
    }

    var row = document.createElement("tr");
    row.setAttribute("data-offline-temp-id", action.id);
    row.innerHTML =
      "<td>" +
      name +
      createPendingBadge("create product") +
      "</td>" +
      "<td>" +
      price +
      "</td>" +
      '<td><span class="tag">Queued</span></td>' +
      '<td><span class="muted">Will sync when online</span></td>';

    if (tbody.firstElementChild && tbody.firstElementChild.querySelector(".empty")) {
      tbody.innerHTML = "";
    }
    tbody.prepend(row);
  }

  function optimisticAppendSale(action) {
    var tbody = document.getElementById("sales-table-body");
    if (!tbody) {
      return;
    }

    var productText = "Product";
    var quantity = "1";
    var amount = "0.00";

    var productSelect = document.getElementById("sale_product");
    if (productSelect && productSelect.options.length > 0) {
      var selected = productSelect.options[productSelect.selectedIndex];
      if (selected && selected.textContent) {
        productText = selected.textContent.trim();
      }
    }

    for (var i = 0; i < action.pairs.length; i += 1) {
      var pair = action.pairs[i];
      if (pair[0] === "sale_quantity") {
        quantity = pair[1];
      }
      if (pair[0] === "sale_amount") {
        amount = pair[1] || amount;
      }
    }

    var row = document.createElement("tr");
    row.setAttribute("data-offline-temp-id", action.id);
    row.innerHTML =
      "<td>Now</td>" +
      "<td>" +
      productText +
      createPendingBadge("record sale") +
      "</td>" +
      "<td>" +
      quantity +
      "</td>" +
      "<td>" +
      amount +
      "</td>" +
      '<td><span class="muted">Will sync when online</span></td>';

    if (tbody.firstElementChild && tbody.firstElementChild.querySelector(".empty")) {
      tbody.innerHTML = "";
    }
    tbody.prepend(row);
  }

  function optimisticDeleteRow(form, action) {
    var row = form.closest("tr");
    if (!row) {
      return;
    }

    row.setAttribute("data-offline-temp-id", action.id);
    row.style.opacity = "0.55";

    var actionCell = row.lastElementChild;
    if (actionCell) {
      actionCell.innerHTML = '<span class="muted">Delete queued for sync</span>';
    }
  }

  function applyOptimisticChange(form, action) {
    if (action.kind === "product-create") {
      optimisticAppendProduct(action);
      return;
    }

    if (action.kind === "sale-create") {
      optimisticAppendSale(action);
      if (typeof window.updateSaleTotal === "function") {
        form.reset();
        window.updateSaleTotal();
      }
      return;
    }

    if (action.kind === "product-delete" || action.kind === "sale-delete") {
      optimisticDeleteRow(form, action);
    }
  }

  function inferActionKind(form) {
    var url = form.getAttribute("action") || "";

    if (url.indexOf("/products/add/") === 0) {
      return "product-create";
    }

    if (url.indexOf("/sales/record/") === 0) {
      return "sale-create";
    }

    if (/^\/products\/\d+\/delete\/$/.test(url)) {
      return "product-delete";
    }

    if (/^\/sales\/\d+\/delete\/$/.test(url)) {
      return "sale-delete";
    }

    if (/^\/products\/\d+\/edit\/$/.test(url)) {
      return "product-edit";
    }

    return "generic-post";
  }

  function inferScope(kind) {
    if (kind.indexOf("product") === 0) {
      return "products";
    }
    if (kind.indexOf("sale") === 0) {
      return "sales";
    }
    return "general";
  }

  function isQueueableForm(form) {
    if (!form || form.tagName !== "FORM") {
      return false;
    }

    var method = (form.getAttribute("method") || "GET").toUpperCase();
    if (method !== "POST") {
      return false;
    }

    if (form.getAttribute("data-offline-queue") !== "true") {
      return false;
    }

    var action = form.getAttribute("action") || "";
    if (!action || action.indexOf("/") !== 0) {
      return false;
    }

    return true;
  }

  function getSyncBannerElements() {
    return {
      root: document.getElementById("sync-status-banner"),
      text: document.getElementById("sync-status-text"),
      flushBtn: document.getElementById("sync-now-btn"),
    };
  }

  function updateSyncBanner() {
    var nodes = getSyncBannerElements();
    if (!nodes.root || !nodes.text) {
      return;
    }

    var queue = readQueue();
    var count = queue.length;
    var online = navigator.onLine;

    if (!online) {
      nodes.root.style.display = "flex";
      nodes.text.textContent = count > 0 ? "Offline. " + count + " action(s) queued." : "Offline mode. New actions will be queued.";
      return;
    }

    if (count > 0) {
      nodes.root.style.display = "flex";
      nodes.text.textContent = syncing ? "Syncing queued actions..." : count + " queued action(s) waiting to sync.";
      return;
    }

    nodes.root.style.display = "none";
    nodes.text.textContent = "";
  }

  async function sendAction(action) {
    var response = await fetch(action.url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "HX-Request": "true",
      },
      body: pairsToBody(action.pairs),
    });

    if (!response.ok) {
      throw new Error("Sync failed with status " + response.status);
    }
  }

  async function flushQueue() {
    if (syncing || !navigator.onLine) {
      updateSyncBanner();
      return;
    }

    var queue = readQueue();
    if (!queue.length) {
      updateSyncBanner();
      return;
    }

    syncing = true;
    updateSyncBanner();

    while (queue.length && navigator.onLine) {
      var action = queue[0];
      try {
        await sendAction(action);
        queue.shift();
        writeQueue(queue);
        dispatchSuccessEvents(action);

        var optimistic = document.querySelector('[data-offline-temp-id="' + action.id + '"]');
        if (optimistic) {
          optimistic.remove();
        }
      } catch (error) {
        break;
      }
    }

    syncing = false;
    updateSyncBanner();
  }

  function buildActionFromForm(form) {
    var kind = inferActionKind(form);
    var formData = new FormData(form);
    return {
      id: "q-" + Date.now() + "-" + Math.random().toString(16).slice(2),
      createdAt: new Date().toISOString(),
      method: "POST",
      url: form.getAttribute("action") || "",
      pairs: formDataToPairs(formData),
      kind: kind,
      scope: inferScope(kind),
      successEvent: form.getAttribute("data-offline-success-event") || "",
    };
  }

  function maybeConfirm(form) {
    var msg = form.getAttribute("hx-confirm") || form.getAttribute("data-confirm") || "";
    if (!msg) {
      return true;
    }

    return window.confirm(msg);
  }

  function installFormInterception() {
    document.addEventListener(
      "submit",
      function (event) {
        var form = event.target;
        if (!isQueueableForm(form)) {
          return;
        }

        if (navigator.onLine) {
          return;
        }

        if (!maybeConfirm(form)) {
          event.preventDefault();
          event.stopPropagation();
          return;
        }

        event.preventDefault();
        event.stopImmediatePropagation();

        var action = buildActionFromForm(form);
        enqueue(action);
        applyOptimisticChange(form, action);
        updateSyncBanner();
      },
      true
    );
  }

  function installSyncTriggers() {
    window.addEventListener("online", function () {
      updateSyncBanner();
      flushQueue();
    });

    window.addEventListener("offline", function () {
      updateSyncBanner();
    });

    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible" && navigator.onLine) {
        flushQueue();
      }
    });

    var nodes = getSyncBannerElements();
    if (nodes.flushBtn) {
      nodes.flushBtn.addEventListener("click", function () {
        flushQueue();
      });
    }

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.addEventListener("message", function (event) {
        if (event && event.data && event.data.type === "JAMBOPOS_SYNC_REQUESTED") {
          flushQueue();
        }
      });
    }
  }

  function tryRegisterBackgroundSync() {
    if (!("serviceWorker" in navigator)) {
      return;
    }

    navigator.serviceWorker.ready
      .then(function (registration) {
        if (!registration.sync) {
          return;
        }
        return registration.sync.register("jambopos-sync");
      })
      .catch(function () {
        return null;
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    installFormInterception();
    installSyncTriggers();
    updateSyncBanner();

    if (navigator.onLine) {
      flushQueue();
    }

    tryRegisterBackgroundSync();
  });
})();