// Global state
let activeTab = "dashboard-tab";
let registrationActive = false;
let scannerActive = false;
let scannerLogInterval = null;
let currentCaptureCount = 0;
const maxCaptures = 5;

// Elements
const menuItems = document.querySelectorAll(".menu-item");
const tabContents = document.querySelectorAll(".tab-content");

// DOM Content Loaded Initializer
document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupTabNavigation();
    setupDashboard();
    setupRegistration();
    setupTraining();
    setupScanner();
    setupTeacherPortal();
    setupStudentERP();
    setupRecords();
    setupPortalLockSimulation();
});

function initApp() {
    refreshStats();
    loadStudentRegistry();
}

// --------------------------------------------------
// PORTAL LOCK SIMULATION (5 PM LOCK)
// --------------------------------------------------
function setupPortalLockSimulation() {
    const lockToggle = document.getElementById("sim-portal-lock");
    const lockScreen = document.getElementById("portal-lock-screen");
    const bypassBtn = document.getElementById("btn-lock-bypass");
    
    // Check real-time hour (locked between 5 PM and 8 AM)
    const currentHour = new Date().getHours();
    if (currentHour >= 17 || currentHour < 8) {
        lockToggle.checked = true;
        lockScreen.style.display = "flex";
    }

    lockToggle.addEventListener("change", () => {
        if (lockToggle.checked) {
            lockScreen.style.display = "flex";
            // Make sure camera is closed if open
            if (registrationActive) stopRegistrationCamera();
            if (scannerActive) stopScannerCamera();
        } else {
            lockScreen.style.display = "none";
        }
    });

    if (bypassBtn) {
        bypassBtn.addEventListener("click", () => {
            lockToggle.checked = false;
            lockScreen.style.display = "none";
        });
    }
}

// --------------------------------------------------
// TAB NAVIGATION LOGIC
// --------------------------------------------------
function setupTabNavigation() {
    menuItems.forEach(item => {
        item.addEventListener("click", () => {
            const target = item.getAttribute("data-target");
            switchTab(target);
        });
    });
}

function switchTab(tabId) {
    menuItems.forEach(item => {
        if (item.getAttribute("data-target") === tabId) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    tabContents.forEach(content => {
        if (content.id === tabId) {
            content.classList.add("active");
        } else {
            content.classList.remove("active");
        }
    });

    if (activeTab === "register-tab" && tabId !== "register-tab") {
        stopRegistrationCamera();
    }
    if (activeTab === "scanner-tab" && tabId !== "scanner-tab") {
        stopScannerCamera();
    }

    activeTab = tabId;

    // Load data specific to tabs on activation
    if (tabId === "dashboard-tab") {
        refreshStats();
        loadStudentRegistry();
    } else if (tabId === "records-tab") {
        loadAttendanceRecords();
    } else if (tabId === "teacher-tab") {
        document.getElementById("teacher-date").value = getTodayDateStr();
    } else if (tabId === "erp-tab") {
        loadERPStudentDropdown();
    }
}

// --------------------------------------------------
// TAB 1: DASHBOARD
// --------------------------------------------------
function setupDashboard() {
    document.getElementById("btn-refresh-students").addEventListener("click", () => {
        loadStudentRegistry();
        refreshStats();
    });

    // Event delegation for delete buttons in the table
    const tableBody = document.querySelector("#table-students tbody");
    tableBody.addEventListener("click", async (e) => {
        const btn = e.target.closest(".btn-delete-student");
        if (!btn) return;

        const studentId = btn.getAttribute("data-id");
        const studentName = btn.getAttribute("data-name");

        const confirmed = confirm(`Are you sure you want to delete student "${studentName}" (ID: ${studentId})?\n\nThis will permanently delete:\n1. Their registered biometric face images.\n2. Their local face embeddings.\n3. All daily gate face punches.\n4. All subject-wise attendance records.`);
        
        if (!confirmed) return;

        try {
            const response = await fetch("/api/student/delete", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ student_id: studentId })
            });
            const result = await response.json();

            if (result.success) {
                alert(result.message);
                loadStudentRegistry();
                refreshStats();
                loadERPStudentDropdown(); // Refresh ERP selector
            } else {
                alert("Failed to delete student: " + result.message);
            }
        } catch (err) {
            alert("Error sending delete request.");
            console.error(err);
        }
    });
}

async function refreshStats() {
    try {
        const response = await fetch("/api/stats");
        const stats = await response.json();
        document.getElementById("stat-registered-count").innerText = stats.registered_count;
        document.getElementById("stat-present-count").innerText = stats.present_today;
    } catch (e) {
        console.error("Failed to load statistics:", e);
    }
}

async function loadStudentRegistry() {
    const tableBody = document.querySelector("#table-students tbody");
    const emptyState = document.getElementById("students-empty-state");
    tableBody.innerHTML = "";
    
    try {
        const response = await fetch("/api/students");
        const students = await response.json();
        
        if (students.length === 0) {
            emptyState.style.display = "flex";
            return;
        }
        
        emptyState.style.display = "none";
        students.forEach(student => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td><strong>${student.student_id}</strong></td>
                <td>${student.student_name}</td>
                <td>${student.created_at}</td>
                <td style="text-align: center;">
                    <button class="btn btn-danger btn-small btn-delete-student" data-id="${student.student_id}" data-name="${student.student_name}">
                        <i data-lucide="trash-2"></i> Delete
                    </button>
                </td>
            `;
            tableBody.appendChild(row);
        });
        
        // Re-initialize icons inside table
        lucide.createIcons();
    } catch (e) {
        console.error("Failed to load students registry:", e);
    }
}

// --------------------------------------------------
// TAB 2: REGISTER STUDENT
// --------------------------------------------------
function setupRegistration() {
    const btnStartCam = document.getElementById("btn-start-reg-cam");
    const btnCapture = document.getElementById("btn-capture-face");
    
    btnStartCam.addEventListener("click", startRegistrationFlow);
    btnCapture.addEventListener("click", captureFaceImage);
}

function addRegLog(msg, type = "") {
    const logsContainer = document.getElementById("reg-logs");
    const placeholder = logsContainer.querySelector(".log-placeholder");
    if (placeholder) logsContainer.innerHTML = "";
    
    const time = new Date().toLocaleTimeString();
    const line = document.createElement("p");
    line.className = `log-line ${type}`;
    line.innerHTML = `<span style="color:#9ca3af;">[${time}]</span> ${msg}`;
    logsContainer.appendChild(line);
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

async function startRegistrationFlow() {
    const studentId = document.getElementById("reg-student-id").value.trim();
    const studentName = document.getElementById("reg-student-name").value.trim();

    if (!studentId || !studentName) {
        alert("Please enter both Student ID and Full Name.");
        return;
    }

    try {
        const response = await fetch("/api/register/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ student_id: studentId, student_name: studentName })
        });
        const result = await response.json();

        if (result.success) {
            document.getElementById("reg-student-id").disabled = true;
            document.getElementById("reg-student-name").disabled = true;
            document.getElementById("btn-start-reg-cam").disabled = true;
            document.getElementById("btn-capture-face").disabled = false;

            currentCaptureCount = 0;
            updateRegProgress(0);
            
            const streamImg = document.getElementById("reg-video-stream");
            const placeholder = document.getElementById("reg-cam-placeholder");
            
            placeholder.style.display = "none";
            streamImg.src = "/api/video_feed/register?t=" + new Date().getTime();
            streamImg.style.display = "block";
            
            registrationActive = true;
            addRegLog(`Registration stream opened for ${studentName} (ID: ${studentId}).`);
        } else {
            alert(result.message);
        }
    } catch (e) {
        alert("Failed to initialize registration camera flow.");
        console.error(e);
    }
}

async function captureFaceImage() {
    if (!registrationActive) return;

    try {
        const response = await fetch("/api/register/capture", { method: "POST" });
        const result = await response.json();

        if (result.success) {
            currentCaptureCount++;
            updateRegProgress(currentCaptureCount);
            addRegLog(result.message, "success");

            if (currentCaptureCount >= maxCaptures) {
                completeRegistration();
            }
        } else {
            addRegLog(result.message, "error");
        }
    } catch (e) {
        addRegLog("Error sending capture request.", "error");
        console.error(e);
    }
}

function updateRegProgress(count) {
    const percentage = (count / maxCaptures) * 100;
    document.getElementById("reg-progress-fill").style.width = `${percentage}%`;
    document.getElementById("reg-progress-text").innerText = `Captured: ${count} / ${maxCaptures}`;
}

async function completeRegistration() {
    try {
        const response = await fetch("/api/register/save", { method: "POST" });
        const result = await response.json();
        
        if (result.success) {
            addRegLog("Database registration committed successfully!", "success");
            alert("Registration completed successfully!\nPlease proceed to 'Train Encodings' to update face data.");
            
            stopRegistrationCamera();
            document.getElementById("form-register").reset();
            switchTab("dashboard-tab");
        } else {
            alert("Failed to save registration: " + result.message);
            stopRegistrationCamera();
        }
    } catch (e) {
        alert("Error finalising registration database.");
        stopRegistrationCamera();
    }
}

function stopRegistrationCamera() {
    registrationActive = false;
    document.getElementById("reg-student-id").disabled = false;
    document.getElementById("reg-student-name").disabled = false;
    document.getElementById("btn-start-reg-cam").disabled = false;
    document.getElementById("btn-capture-face").disabled = true;

    const streamImg = document.getElementById("reg-video-stream");
    const placeholder = document.getElementById("reg-cam-placeholder");
    
    streamImg.src = "";
    streamImg.style.display = "none";
    placeholder.style.display = "flex";
    
    fetch("/api/camera/release", { method: "POST" }).catch(e => console.log(e));
}

// --------------------------------------------------
// TAB 3: TRAIN ENCODINGS
// --------------------------------------------------
function setupTraining() {
    document.getElementById("btn-run-train").addEventListener("click", () => runTrainingFlow(false));
    document.getElementById("btn-force-train").addEventListener("click", () => runTrainingFlow(true));
}

async function runTrainingFlow(force = false) {
    const logsContainer = document.getElementById("train-logs");
    const btnRun = document.getElementById("btn-run-train");
    const btnForce = document.getElementById("btn-force-train");
    
    btnRun.disabled = true;
    btnForce.disabled = true;
    
    logsContainer.innerHTML = `<p class="term-line">> Starting training execution (Force: ${force})...</p>`;
    
    try {
        const response = await fetch("/api/train", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ force: force })
        });
        const result = await response.json();
        
        if (result.success) {
            logsContainer.innerHTML += `<p class="term-line" style="color:#34d399;">> SUCCESS: ${result.message}</p>`;
            alert("Face embeddings updated successfully!");
        } else {
            logsContainer.innerHTML += `<p class="term-line" style="color:#f87171;">> WARNING: ${result.message}</p>`;
            alert(result.message);
        }
    } catch (e) {
        logsContainer.innerHTML += `<p class="term-line" style="color:#f87171;">> ERROR: Connection failed.</p>`;
        alert("Training backend failed.");
    } finally {
        btnRun.disabled = false;
        btnForce.disabled = false;
    }
}

// --------------------------------------------------
// TAB 4: LIVE SCANNER
// --------------------------------------------------
function setupScanner() {
    const btnStart = document.getElementById("btn-start-scanner");
    const btnStop = document.getElementById("btn-stop-scanner");
    
    btnStart.addEventListener("click", startScannerCamera);
    btnStop.addEventListener("click", stopScannerCamera);
}

function startScannerCamera() {
    const streamImg = document.getElementById("scanner-video-stream");
    const placeholder = document.getElementById("scanner-cam-placeholder");
    const badge = document.getElementById("scanner-badge");
    const btnStart = document.getElementById("btn-start-scanner");
    const btnStop = document.getElementById("btn-stop-scanner");
    
    btnStart.disabled = true;
    btnStop.disabled = false;
    badge.innerText = "ACTIVE SCANNING";
    badge.className = "badge active";
    
    placeholder.style.display = "none";
    streamImg.src = "/api/video_feed/attendance?t=" + new Date().getTime();
    streamImg.style.display = "block";
    
    scannerActive = true;
    
    const sessionLogs = document.getElementById("session-logs-container");
    sessionLogs.innerHTML = "";
    
    fetchTodaySessionLogs();
    scannerLogInterval = setInterval(fetchTodaySessionLogs, 2000);
}

function stopScannerCamera() {
    if (!scannerActive) return;
    
    const streamImg = document.getElementById("scanner-video-stream");
    const placeholder = document.getElementById("scanner-cam-placeholder");
    const badge = document.getElementById("scanner-badge");
    const btnStart = document.getElementById("btn-start-scanner");
    const btnStop = document.getElementById("btn-stop-scanner");
    
    btnStart.disabled = false;
    btnStop.disabled = true;
    badge.innerText = "INACTIVE";
    badge.className = "badge";
    
    streamImg.src = "";
    streamImg.style.display = "none";
    placeholder.style.display = "flex";
    
    scannerActive = false;
    
    if (scannerLogInterval) {
        clearInterval(scannerLogInterval);
        scannerLogInterval = null;
    }
    
    fetch("/api/camera/release", { method: "POST" }).catch(e => console.log(e));
}

async function fetchTodaySessionLogs() {
    if (!scannerActive) return;
    
    try {
        const response = await fetch("/api/logs?date=" + getTodayDateStr());
        const logs = await response.json();
        
        const container = document.getElementById("session-logs-container");
        
        if (logs.length === 0) {
            container.innerHTML = `
                <div class="session-log-placeholder" id="session-log-empty">
                    <i data-lucide="list-todo"></i>
                    <p>Logs will update here when faces are detected and attendance is recorded.</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }
        
        const emptyState = document.getElementById("session-log-empty");
        if (emptyState) container.innerHTML = "";
        
        logs.forEach(log => {
            const itemId = `session-log-${log.id}`;
            let item = document.getElementById(itemId);
            
            if (!item) {
                item = document.createElement("div");
                item.id = itemId;
                item.className = "session-log-item";
                item.innerHTML = `
                    <div class="session-log-icon">
                        <i data-lucide="check"></i>
                    </div>
                    <div class="session-log-details">
                        <h4>${log.student_name} (${log.student_id})</h4>
                        <span>Checked in at: ${log.time} | Present</span>
                    </div>
                `;
                container.insertBefore(item, container.firstChild);
            }
        });
        
        lucide.createIcons();
    } catch (e) {
        console.error("Failed to load live scanner logs:", e);
    }
}

// --------------------------------------------------
// TAB 5: TEACHER ERP PORTAL (BLURRING & REQUIREMENT)
// --------------------------------------------------
function setupTeacherPortal() {
    document.getElementById("btn-teacher-today").addEventListener("click", () => {
        document.getElementById("teacher-date").value = getTodayDateStr();
    });
    
    document.getElementById("btn-load-class-list").addEventListener("click", loadTeacherClassList);
    document.getElementById("btn-submit-subject-attendance").addEventListener("click", submitTeacherAttendance);
}

async function loadTeacherClassList() {
    const subject = document.getElementById("teacher-subject").value;
    const date = document.getElementById("teacher-date").value.trim();
    
    if (!date) {
        alert("Please enter a target date.");
        return;
    }
    
    const tableBody = document.querySelector("#table-teacher-attendance tbody");
    tableBody.innerHTML = `<tr><td colspan="4" class="text-center-placeholder">Querying class registry list...</td></tr>`;
    document.getElementById("btn-submit-subject-attendance").disabled = true;
    
    try {
        const response = await fetch(`/api/teacher/students?subject=${subject}&date=${date}`);
        const students = await response.json();
        
        tableBody.innerHTML = "";
        
        if (students.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="4" class="text-center-placeholder">No registered students found.</td></tr>`;
            return;
        }
        
        students.forEach(s => {
            const row = document.createElement("tr");
            
            // Determine elements based on gate punch (has_punched)
            let punchBadge = "";
            let nameClass = "";
            let rowClass = "";
            let inputState = "";
            let checkedPresent = "";
            let checkedAbsent = "";
            
            if (s.has_punched) {
                punchBadge = `<span class="badge active"><i data-lucide="shield-check" style="width:12px; height:12px; display:inline-block; vertical-align:middle;"></i> PUNCH OK</span>`;
                // Set radio checked based on saved status (defaults to Present if not marked yet)
                if (s.saved_status === "Absent") {
                    checkedAbsent = "checked";
                } else {
                    checkedPresent = "checked";
                }
            } else {
                punchBadge = `<span class="badge"><i data-lucide="shield-alert" style="width:12px; height:12px; display:inline-block; vertical-align:middle;"></i> NO GATE ENTRY</span>`;
                nameClass = "blurred-name";
                rowClass = "blurred-row";
                inputState = "disabled";
                // Lockout as Absent
                checkedAbsent = "checked";
            }
            
            row.className = rowClass;
            row.innerHTML = `
                <td><strong>${s.student_id}</strong></td>
                <td><span class="${nameClass}" title="${s.has_punched ? s.student_name : 'No biometric scan recorded for this date'}">${s.student_name}</span></td>
                <td style="text-align: center;">${punchBadge}</td>
                <td style="text-align: center;">
                    <div class="radio-group-attendance">
                        <label class="radio-option">
                            <input type="radio" name="status-${s.student_id}" value="Present" ${checkedPresent} ${inputState}>
                            <span>Present</span>
                        </label>
                        <label class="radio-option">
                            <input type="radio" name="status-${s.student_id}" value="Absent" ${checkedAbsent} ${inputState}>
                            <span>Absent</span>
                        </label>
                    </div>
                </td>
            `;
            tableBody.appendChild(row);
        });
        
        lucide.createIcons();
        document.getElementById("btn-submit-subject-attendance").disabled = false;
    } catch (e) {
        tableBody.innerHTML = `<tr><td colspan="4" class="text-center-placeholder" style="color:var(--danger);">Error loading students class list.</td></tr>`;
        console.error(e);
    }
}

async function submitTeacherAttendance() {
    const subject = document.getElementById("teacher-subject").value;
    const date = document.getElementById("teacher-date").value.trim();
    
    // Collect rows inputs
    const rows = document.querySelectorAll("#table-teacher-attendance tbody tr");
    const attendanceData = [];
    
    rows.forEach(row => {
        const studentId = row.querySelector("td strong").innerText;
        const statusVal = row.querySelector(`input[name="status-${studentId}"]:checked`).value;
        attendanceData.push({
            student_id: studentId,
            status: statusVal
        });
    });
    
    const btnSubmit = document.getElementById("btn-submit-subject-attendance");
    btnSubmit.disabled = true;
    
    try {
        const response = await fetch("/api/teacher/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                subject_code: subject,
                date: date,
                attendance: attendanceData
            })
        });
        const result = await response.json();
        
        if (result.success) {
            alert("Subject attendance submitted successfully!");
            loadTeacherClassList(); // Reload
        } else {
            alert("Failed to submit: " + result.message);
            btnSubmit.disabled = false;
        }
    } catch (e) {
        alert("Error submitting attendance to database.");
        btnSubmit.disabled = false;
        console.error(e);
    }
}

// --------------------------------------------------
// TAB 6: STUDENT ERP (SUBJECT SUMMARIES & ATTENDANCE MATRIX)
// --------------------------------------------------
function setupStudentERP() {
    document.getElementById("erp-student-select").addEventListener("change", loadStudentERPData);
}

async function loadERPStudentDropdown() {
    const select = document.getElementById("erp-student-select");
    const previousVal = select.value;
    
    select.innerHTML = `<option value="">-- Choose Student --</option>`;
    
    try {
        const response = await fetch("/api/students");
        const students = await response.json();
        
        students.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.student_id;
            opt.innerText = `${s.student_name} (${s.student_id})`;
            select.appendChild(opt);
        });
        
        if (previousVal && [...select.options].some(o => o.value === previousVal)) {
            select.value = previousVal;
        }
    } catch (e) {
        console.error("Failed to load ERP students selector:", e);
    }
}

async function loadStudentERPData() {
    const studentId = document.getElementById("erp-student-select").value;
    
    const infoCard = document.getElementById("erp-student-info-card");
    const erpGrids = document.getElementById("erp-data-grids");
    
    if (!studentId) {
        infoCard.style.display = "none";
        erpGrids.style.display = "none";
        return;
    }
    
    try {
        const response = await fetch(`/api/student/erp?student_id=${studentId}`);
        const data = await response.json();
        
        // Populate Student Header
        document.getElementById("erp-info-prn").innerText = data.prn_no;
        document.getElementById("erp-info-name").innerText = data.student_name;
        
        // Populate Left: Subject Summary List Table
        const summaryBody = document.querySelector("#table-erp-summary tbody");
        summaryBody.innerHTML = "";
        
        data.summaries.forEach(sub => {
            const row = document.createElement("tr");
            
            // Color code low attendance below 75%
            const pctClass = sub.attendance_percentage < 75 ? "crit-low" : "crit-ok";
            
            row.innerHTML = `
                <td>No</td>
                <td><strong>${sub.subject_code}</strong><br><span style="font-size:10px; color:var(--text-secondary);">${sub.subject_name}</span></td>
                <td>${sub.total_lectures}</td>
                <td>${sub.present_lectures}</td>
                <td><span class="${pctClass}">${sub.attendance_percentage}%</span></td>
            `;
            summaryBody.appendChild(row);
        });
        
        // Populate Right: Matrix Table
        const matrixBody = document.querySelector("#table-erp-matrix tbody");
        matrixBody.innerHTML = "";
        
        if (data.matrix.length === 0) {
            matrixBody.innerHTML = `<tr><td colspan="7" class="text-center-placeholder">No lecture attendance logs found for this student.</td></tr>`;
        } else {
            data.matrix.forEach(row => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${row.date}</strong></td>
                    <td>${row.day}</td>
                    <td style="text-align:center; font-weight:bold; color:${row.INF45011 === 'P' ? 'var(--success)' : (row.INF45011 === 'A' ? 'var(--danger)' : 'var(--text-secondary)')}">${row.INF45011}</td>
                    <td style="text-align:center; font-weight:bold; color:${row.INF45021 === 'P' ? 'var(--success)' : (row.INF45021 === 'A' ? 'var(--danger)' : 'var(--text-secondary)')}">${row.INF45021}</td>
                    <td style="text-align:center; font-weight:bold; color:${row.INF45022 === 'P' ? 'var(--success)' : (row.INF45022 === 'A' ? 'var(--danger)' : 'var(--text-secondary)')}">${row.INF45022}</td>
                    <td style="text-align:center; font-weight:bold; color:${row.INF45112 === 'P' ? 'var(--success)' : (row.INF45112 === 'A' ? 'var(--danger)' : 'var(--text-secondary)')}">${row.INF45112}</td>
                    <td style="text-align:center; font-weight:bold; color:${row.CVLAB === 'P' ? 'var(--success)' : (row.CVLAB === 'A' ? 'var(--danger)' : 'var(--text-secondary)')}">${row.CVLAB}</td>
                `;
                matrixBody.appendChild(tr);
            });
        }
        
        infoCard.style.display = "block";
        erpGrids.style.display = "grid";
    } catch (e) {
        alert("Failed to load ERP logs.");
        console.error(e);
    }
}

// --------------------------------------------------
// TAB 7: VIEW LOGS HISTORY (DAILY GATE)
// --------------------------------------------------
function setupRecords() {
    document.getElementById("btn-apply-filters").addEventListener("click", loadAttendanceRecords);
    document.getElementById("btn-clear-filters").addEventListener("click", () => {
        document.getElementById("filter-search").value = "";
        document.getElementById("filter-date").value = "";
        loadAttendanceRecords();
    });
    
    document.getElementById("btn-filter-today").addEventListener("click", () => {
        document.getElementById("filter-date").value = getTodayDateStr();
    });
    
    document.getElementById("btn-export-records").addEventListener("click", exportRecordsToCSV);
}

async function loadAttendanceRecords() {
    const tableBody = document.querySelector("#table-records tbody");
    const emptyState = document.getElementById("records-empty-state");
    tableBody.innerHTML = "";
    
    const searchVal = document.getElementById("filter-search").value.trim();
    const dateVal = document.getElementById("filter-date").value.trim();
    
    let url = "/api/logs";
    const params = [];
    if (searchVal) params.push(`search=${encodeURIComponent(searchVal)}`);
    if (dateVal) params.push(`date=${encodeURIComponent(dateVal)}`);
    
    if (params.length > 0) url += "?" + params.join("&");
    
    try {
        const response = await fetch(url);
        const logs = await response.json();
        
        if (logs.length === 0) {
            emptyState.style.display = "flex";
            return;
        }
        
        emptyState.style.display = "none";
        logs.forEach(log => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${log.id}</td>
                <td><strong>${log.student_id}</strong></td>
                <td>${log.student_name}</td>
                <td>${log.date}</td>
                <td>${log.time}</td>
                <td><span style="color:var(--success); font-weight:600;">${log.status}</span></td>
            `;
            tableBody.appendChild(row);
        });
    } catch (e) {
        console.error("Failed to load records table:", e);
    }
}

async function exportRecordsToCSV() {
    const searchVal = document.getElementById("filter-search").value.trim();
    const dateVal = document.getElementById("filter-date").value.trim();
    
    try {
        const response = await fetch("/api/export", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ search: searchVal, date: dateVal })
        });
        const result = await response.json();
        
        if (result.success) {
            const downloadUrl = `/api/download?path=${encodeURIComponent(result.filepath)}`;
            const link = document.createElement("a");
            link.href = downloadUrl;
            link.setAttribute("download", result.filename);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } else {
            alert("Export Failed: " + result.message);
        }
    } catch (e) {
        alert("Error exporting CSV.");
        console.error(e);
    }
}

// Helper date builder (returns DD-MM-YYYY)
function getTodayDateStr() {
    const now = new Date();
    const day = String(now.getDate()).padStart(2, '0');
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const year = now.getFullYear();
    return `${day}-${month}-${year}`;
}
