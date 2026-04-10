document.addEventListener('DOMContentLoaded', () => {
    const API_BASE = (window.APP_CONFIG && window.APP_CONFIG.apiBaseUrl)
        ? window.APP_CONFIG.apiBaseUrl.replace(/\/$/, '')
        : '';

    function apiUrl(path) {
        return API_BASE ? `${API_BASE}${path}` : path;
    }

    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const uploadPreview = document.getElementById('upload-preview');
    const previewVideo = document.getElementById('preview-video');
    const fileName = document.getElementById('file-name');
    const fileSize = document.getElementById('file-size');
    const removeBtn = document.getElementById('remove-btn');
    const analyzeBtn = document.getElementById('analyze-btn');
    const sampleBtn = document.getElementById('sample-btn');

    const uploadSection = document.getElementById('upload-section');
    const processingSection = document.getElementById('processing-section');
    const resultsSection = document.getElementById('results-section');
    const errorSection = document.getElementById('error-section');

    const processingStage = document.getElementById('processing-stage');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const pipelineStages = document.querySelectorAll('.stage-item');
    const stageConnectors = document.querySelectorAll('.stage-connector');

    const resultVideo = document.getElementById('result-video');
    const downloadBtn = document.getElementById('download-btn');
    const newAnalysisBtn = document.getElementById('new-analysis-btn');
    const retryBtn = document.getElementById('retry-btn');
    const errorMessage = document.getElementById('error-message');

    let selectedFile = null;
    let currentTaskId = null;
    let pollInterval = null;

    function formatFileSize(bytes) {
        if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(1) + ' GB';
        if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + ' MB';
        if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return bytes + ' B';
    }

    function showSection(section) {
        [uploadSection, processingSection, resultsSection, errorSection].forEach(s => {
            s.classList.remove('active');
            if (s === uploadSection) {
                s.style.display = 'none';
            }
        });

        if (section === uploadSection) {
            section.style.display = '';
        } else {
            section.classList.add('active');
        }
    }

    function resetUpload() {
        selectedFile = null;
        fileInput.value = '';
        uploadZone.style.display = '';
        uploadPreview.classList.remove('active');
        previewVideo.src = '';
    }

    function showPreview(file) {
        selectedFile = file;
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        previewVideo.src = URL.createObjectURL(file);
        uploadZone.style.display = 'none';
        uploadPreview.classList.add('active');
    }

    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadZone.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            const ext = file.name.split('.').pop().toLowerCase();
            if (['mp4', 'avi', 'mov', 'mkv'].includes(ext)) {
                showPreview(file);
            } else {
                alert('Invalid file format. Please use MP4, AVI, MOV, or MKV.');
            }
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            showPreview(e.target.files[0]);
        }
    });

    removeBtn.addEventListener('click', () => resetUpload());

    analyzeBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        const formData = new FormData();
        formData.append('video', selectedFile);

        showSection(processingSection);

        try {
            const res = await fetch(apiUrl('/api/upload'), { method: 'POST', body: formData });
            const data = await res.json();

            if (data.error) {
                showError(data.error);
                return;
            }

            currentTaskId = data.task_id;
            startPolling();
        } catch (err) {
            showError('Failed to upload video. Please try again.');
        }
    });

    sampleBtn.addEventListener('click', async () => {
        showSection(processingSection);
        sampleBtn.disabled = true;

        try {
            const res = await fetch(apiUrl('/api/sample'), { method: 'POST' });
            const data = await res.json();

            if (data.error) {
                showError(data.error);
                sampleBtn.disabled = false;
                return;
            }

            currentTaskId = data.task_id;
            startPolling();
        } catch (err) {
            showError('Failed to start sample processing. Please try again.');
            sampleBtn.disabled = false;
        }
    });

    function startPolling() {
        resetProgress();
        pollInterval = setInterval(async () => {
            try {
                const res = await fetch(apiUrl(`/api/status/${currentTaskId}`));
                const data = await res.json();

                updateProgress(data);

                if (data.status === 'complete') {
                    clearInterval(pollInterval);
                    pollInterval = null;
                    setTimeout(() => showResults(), 600);
                } else if (data.status === 'error') {
                    clearInterval(pollInterval);
                    pollInterval = null;
                    showError(data.error || 'An unexpected error occurred during processing.');
                }
            } catch (err) {
                clearInterval(pollInterval);
                pollInterval = null;
                showError('Connection lost. Please check server status.');
            }
        }, 1000);
    }

    function resetProgress() {
        progressBar.style.width = '0%';
        progressText.textContent = '0%';
        processingStage.textContent = 'Initializing pipeline...';

        pipelineStages.forEach(s => {
            s.classList.remove('active', 'complete');
        });
        stageConnectors.forEach(c => {
            c.classList.remove('active');
        });
    }

    function updateProgress(data) {
        const progress = data.progress || 0;
        progressBar.style.width = progress + '%';
        progressText.textContent = Math.round(progress) + '%';

        if (data.stage) {
            processingStage.textContent = data.stage;
        }

        const stageItems = document.querySelectorAll('.stage-item');
        const connectors = document.querySelectorAll('.stage-connector');

        let connectorIdx = 0;
        stageItems.forEach((item, idx) => {
            const threshold = parseInt(item.dataset.threshold);
            item.classList.remove('active', 'complete');

            if (progress >= threshold) {
                const nextItem = stageItems[idx + 1];
                const nextThreshold = nextItem ? parseInt(nextItem.dataset.threshold) : 101;

                if (progress < nextThreshold) {
                    item.classList.add('active');
                } else {
                    item.classList.add('complete');
                }
            }

            if (idx < stageItems.length - 1) {
                const connector = connectors[connectorIdx];
                if (connector && progress >= threshold) {
                    connector.classList.add('active');
                }
                connectorIdx++;
            }
        });
    }

    function showResults() {
        showSection(resultsSection);
        resultVideo.src = apiUrl(`/api/video/${currentTaskId}`);
        resultVideo.load();
        sampleBtn.disabled = false;
    }

    function showError(msg) {
        showSection(errorSection);
        errorMessage.textContent = msg;
        sampleBtn.disabled = false;
    }

    downloadBtn.addEventListener('click', () => {
        if (currentTaskId) {
            window.location.href = apiUrl(`/api/download/${currentTaskId}`);
        }
    });

    newAnalysisBtn.addEventListener('click', () => {
        resetUpload();
        showSection(uploadSection);
        currentTaskId = null;
    });

    retryBtn.addEventListener('click', () => {
        resetUpload();
        showSection(uploadSection);
        currentTaskId = null;
    });

    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
            e.preventDefault();
            const target = document.querySelector(anchor.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
});
