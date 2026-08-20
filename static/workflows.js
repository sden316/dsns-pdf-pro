const MODES = {
  merge: {
    accept: "application/pdf,image/jpeg,image/png,.pdf,.jpg,.jpeg,.png",
    allowedExtensions: new Set(["pdf", "jpg", "jpeg", "png"]),
    endpoint: "/api/merge",
    minimumFiles: 2,
    outputName: "merged.pdf",
    labels: {
      count: "Files",
      dropDescription: "PDF, JPG, JPEG, and PNG files merge in the order shown below",
      dropMark: "FILES",
      dropTitle: "Choose PDF or image files",
      empty: "No files selected.",
      open: "Open files",
      output: "Merged document",
      submit: "Merge & Save",
      title: "Selected files",
    },
  },
  images: {
    accept: "image/jpeg,image/png,.jpg,.jpeg,.png",
    allowedExtensions: new Set(["jpg", "jpeg", "png"]),
    endpoint: "/api/images-to-pdf",
    minimumFiles: 1,
    outputName: "images.pdf",
    labels: {
      count: "Images",
      dropDescription: "JPG, JPEG, and PNG images become one PDF page each",
      dropMark: "IMG",
      dropTitle: "Choose image files",
      empty: "No images selected.",
      open: "Open images",
      output: "Converted document",
      submit: "Convert & Save",
      title: "Selected images",
    },
  },
};

const state = {
  busy: false,
  files: {
    images: [],
    merge: [],
  },
  mode: "merge",
  outputNames: {
    images: MODES.images.outputName,
    merge: MODES.merge.outputName,
  },
};

const elements = {
  background: document.querySelector("#background"),
  clearButton: document.querySelector("#clear-button"),
  dropDescription: document.querySelector("#drop-description"),
  dropMark: document.querySelector("#drop-mark"),
  dropTitle: document.querySelector("#drop-title"),
  dropZone: document.querySelector("#drop-zone"),
  emptyState: document.querySelector("#empty-state"),
  fileCount: document.querySelector("#file-count"),
  fileCountLabel: document.querySelector("#file-count-label"),
  fileInput: document.querySelector("#file-input"),
  fileList: document.querySelector("#file-list"),
  imageFit: document.querySelector("#image-fit"),
  imageSettings: document.querySelector("#image-settings"),
  marginMm: document.querySelector("#margin-mm"),
  mergeButton: document.querySelector("#merge-button"),
  message: document.querySelector("#message"),
  openButton: document.querySelector("#open-button"),
  orientation: document.querySelector("#orientation"),
  outputName: document.querySelector("#output-name"),
  outputState: document.querySelector("#output-state"),
  outputTitle: document.querySelector("#output-title"),
  pageSize: document.querySelector("#page-size"),
  progress: document.querySelector("#progress"),
  totalSize: document.querySelector("#total-size"),
  workspaceTitle: document.querySelector("#workspace-title"),
};

function currentConfig() {
  return MODES[state.mode];
}

function currentFiles() {
  return state.files[state.mode];
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function extensionOf(fileName) {
  return fileName.includes(".") ? fileName.split(".").pop().toLowerCase() : "";
}

function formatBytes(bytes) {
  if (bytes === 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / (1024 ** index)).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function outputFileName() {
  const value = elements.outputName.value.trim() || currentConfig().outputName;
  return value.toLowerCase().endsWith(".pdf") ? value : `${value}.pdf`;
}

function setMessage(text, type = "") {
  elements.message.textContent = text;
  elements.message.className = `message ${type}`.trim();
}

function setBusy(busy) {
  state.busy = busy;
  const files = currentFiles();
  const ready = files.length >= currentConfig().minimumFiles;
  elements.progress.hidden = !busy;
  elements.progress.setAttribute("aria-hidden", String(!busy));
  elements.openButton.disabled = busy;
  elements.clearButton.disabled = busy || files.length === 0;
  elements.mergeButton.disabled = busy || !ready;
  elements.outputName.disabled = busy;
  document.querySelectorAll("button[data-mode]").forEach((button) => {
    button.disabled = busy;
  });
  elements.imageSettings.querySelectorAll("input, select").forEach((control) => {
    control.disabled = busy;
  });
  elements.outputState.textContent = busy ? "Processing" : ready ? "Ready" : "Not ready";
}

function render() {
  const config = currentConfig();
  const files = currentFiles();
  elements.fileList.innerHTML = files.map((file, index) => `
    <li class="file-row">
      <div class="file-index">${String(index + 1).padStart(2, "0")}</div>
      <div class="file-meta">
        <div class="file-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</div>
        <div class="file-size"><span class="file-kind">${escapeHtml(extensionOf(file.name).toUpperCase())}</span> · ${formatBytes(file.size)}</div>
      </div>
      <div class="file-actions">
        <button class="order-button" type="button" data-action="up" data-index="${index}" title="Move up" aria-label="Move ${escapeHtml(file.name)} up" ${index === 0 || state.busy ? "disabled" : ""}>↑</button>
        <button class="order-button" type="button" data-action="down" data-index="${index}" title="Move down" aria-label="Move ${escapeHtml(file.name)} down" ${index === files.length - 1 || state.busy ? "disabled" : ""}>↓</button>
        <button class="remove-button" type="button" data-action="remove" data-index="${index}" title="Remove" aria-label="Remove ${escapeHtml(file.name)}" ${state.busy ? "disabled" : ""}>×</button>
      </div>
    </li>
  `).join("");
  elements.emptyState.hidden = files.length !== 0;
  elements.emptyState.textContent = config.labels.empty;
  elements.fileCount.textContent = files.length;
  elements.fileCountLabel.textContent = config.labels.count;
  elements.totalSize.textContent = formatBytes(files.reduce((total, file) => total + file.size, 0));
  elements.workspaceTitle.textContent = config.labels.title;
  elements.openButton.textContent = config.labels.open;
  elements.dropMark.textContent = config.labels.dropMark;
  elements.dropTitle.textContent = config.labels.dropTitle;
  elements.dropDescription.textContent = config.labels.dropDescription;
  elements.outputTitle.textContent = config.labels.output;
  elements.mergeButton.textContent = config.labels.submit;
  elements.imageSettings.hidden = state.mode !== "images";
  setBusy(state.busy);
}

function switchMode(mode) {
  if (state.busy || !MODES[mode] || mode === state.mode) {
    return;
  }
  state.outputNames[state.mode] = outputFileName();
  state.mode = mode;
  elements.outputName.value = state.outputNames[mode];
  elements.fileInput.accept = currentConfig().accept;
  elements.fileInput.value = "";
  document.querySelectorAll("button[data-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === mode);
  });
  setMessage("");
  render();
}

function addFiles(fileList) {
  const incoming = [...fileList];
  const config = currentConfig();
  const accepted = incoming.filter((file) => config.allowedExtensions.has(extensionOf(file.name)));
  if (accepted.length !== incoming.length) {
    const expected = state.mode === "images" ? "JPG, JPEG, or PNG" : "PDF, JPG, JPEG, or PNG";
    setMessage(`Only ${expected} files were added.`, "error");
  } else {
    setMessage("");
  }
  currentFiles().push(...accepted);
  elements.fileInput.value = "";
  render();
}

function moveFile(from, to) {
  const files = currentFiles();
  const [file] = files.splice(from, 1);
  files.splice(to, 0, file);
  render();
}

async function chooseSaveHandle() {
  if (!("showSaveFilePicker" in window)) {
    return null;
  }
  return window.showSaveFilePicker({
    suggestedName: outputFileName(),
    types: [{
      description: "PDF document",
      accept: { "application/pdf": [".pdf"] },
    }],
  });
}

function appendImageOptions(formData) {
  formData.append("page_size", elements.pageSize.value);
  formData.append("orientation", elements.orientation.value);
  formData.append("margin_mm", elements.marginMm.value);
  formData.append("fit", elements.imageFit.value);
  formData.append("background", elements.background.value);
}

async function processAndSave() {
  let saveHandle;
  try {
    saveHandle = await chooseSaveHandle();
  } catch (error) {
    if (error.name === "AbortError") {
      setMessage("Save canceled.");
      return;
    }
    setMessage(`Could not choose the output location: ${error.message}`, "error");
    return;
  }

  const config = currentConfig();
  setBusy(true);
  setMessage(state.mode === "images" ? "Converting selected images..." : "Merging selected files...");
  try {
    const formData = new FormData();
    currentFiles().forEach((file) => formData.append("files", file, file.name));
    formData.append("output_name", outputFileName());
    if (state.mode === "images") {
      appendImageOptions(formData);
    }
    const response = await fetch(config.endpoint, { method: "POST", body: formData });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.error || `Processing failed with HTTP ${response.status}.`);
    }

    const blob = await response.blob();
    if (saveHandle) {
      const writable = await saveHandle.createWritable();
      await writable.write(blob);
      await writable.close();
      setMessage(`Saved ${outputFileName()} (${formatBytes(blob.size)}).`, "success");
    } else {
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = outputFileName();
      link.click();
      URL.revokeObjectURL(url);
      setMessage(`Download started for ${outputFileName()}.`, "success");
    }
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    state.outputNames[state.mode] = outputFileName();
    setBusy(false);
  }
}

document.querySelectorAll("button[data-mode]").forEach((button) => {
  button.addEventListener("click", () => switchMode(button.dataset.mode));
});
elements.openButton.addEventListener("click", () => elements.fileInput.click());
elements.dropZone.addEventListener("click", () => elements.fileInput.click());
elements.fileInput.addEventListener("change", () => addFiles(elements.fileInput.files));
elements.outputName.addEventListener("input", () => {
  state.outputNames[state.mode] = elements.outputName.value;
});
elements.clearButton.addEventListener("click", () => {
  state.files[state.mode] = [];
  setMessage("");
  render();
});
elements.mergeButton.addEventListener("click", processAndSave);

elements.fileList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button || state.busy) {
    return;
  }
  const index = Number(button.dataset.index);
  const files = currentFiles();
  if (button.dataset.action === "remove") {
    files.splice(index, 1);
    render();
  } else if (button.dataset.action === "up" && index > 0) {
    moveFile(index, index - 1);
  } else if (button.dataset.action === "down" && index < files.length - 1) {
    moveFile(index, index + 1);
  }
});

for (const eventName of ["dragenter", "dragover"]) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.add("dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove("dragging");
  });
}
elements.dropZone.addEventListener("drop", (event) => addFiles(event.dataTransfer.files));

render();
