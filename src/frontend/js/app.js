document.addEventListener("DOMContentLoaded", () => {
    
    // Variables
    const navItems = document.querySelectorAll(".nav-item");
    const views = document.querySelectorAll(".view-container");
    const btnProcess = document.getElementById("btn-process");
    
    // Elements for stats
    const statProcessed = document.getElementById("stat-processed");
    const statPending = document.getElementById("stat-pending");
    const statOthers = document.getElementById("stat-others");
    const statErrors = document.getElementById("stat-errors");

    // Initialize pywebview integration
    // We listen to the pywebviewready event which is fired when window.pywebview is available
    window.addEventListener('pywebviewready', function() {
        showToast("Conectado al motor Python de Oculus.");
        loadStats();
    });

    // Navigation logic
    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            
            // Remove active from all
            navItems.forEach(nav => nav.classList.remove("active"));
            views.forEach(view => view.classList.remove("active"));
            
            // Add active to clicked
            item.classList.add("active");
            const targetView = item.getAttribute("data-view");
            const viewElement = document.getElementById(`view-${targetView}`);
            
            if(viewElement) {
                viewElement.classList.add("active");
                document.getElementById("view-title").textContent = item.querySelector("span").textContent;
                
                // Si es la vista de DTEs, cargar clientes
                if(targetView === "dtes") {
                    loadClients();
                } else if(targetView === "emails") {
                    loadEmails();
                } else if(targetView === "review") {
                    loadReviews();
                } else if(targetView === "explorer") {
                    loadExplorer();
                } else if(targetView === "settings") {
                    loadSettings();
                }
            } else {
                showToast(`Vista ${targetView} en desarrollo.`);
                document.getElementById("view-dashboard").classList.add("active");
            }
        });
    });

    // Process button
    btnProcess.addEventListener("click", async () => {
        btnProcess.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Procesando...';
        btnProcess.disabled = true;
        
        try {
            if(window.pywebview && window.pywebview.api) {
                const result = await window.pywebview.api.start_processing();
                showToast(result);
                // Simulate refresh stats after 2s
                setTimeout(() => {
                    loadStats();
                    btnProcess.innerHTML = '<i class="fa-solid fa-bolt"></i> Extraer Ahora';
                    btnProcess.disabled = false;
                }, 2000);
            } else {
                showToast("Error: API no disponible.");
                btnProcess.innerHTML = '<i class="fa-solid fa-bolt"></i> Extraer Ahora';
                btnProcess.disabled = false;
            }
        } catch (error) {
            showToast("Ocurrió un error.");
            btnProcess.innerHTML = '<i class="fa-solid fa-bolt"></i> Extraer Ahora';
            btnProcess.disabled = false;
        }
    });

    // DTE Generator logic
    const selClient = document.getElementById("sel-client");
    const selMonth = document.getElementById("sel-month");
    const inputPath = document.getElementById("input-path");
    const btnGenerateExcel = document.getElementById("btn-generate-excel");

    async function loadClients() {
        if(window.pywebview && window.pywebview.api) {
            const clients = await window.pywebview.api.get_clients();
            selClient.innerHTML = '<option value="">-- Seleccione un cliente --</option>';
            clients.forEach(c => {
                selClient.innerHTML += `<option value="${c}">${c}</option>`;
            });
        }
    }

    selClient.addEventListener("change", async (e) => {
        const client = e.target.value;
        if(client && window.pywebview && window.pywebview.api) {
            const months = await window.pywebview.api.get_months(client);
            selMonth.innerHTML = '<option value="">-- Seleccione un mes --</option>';
            months.forEach(m => {
                selMonth.innerHTML += `<option value="${m}">${m}</option>`;
            });
            selMonth.disabled = false;
        } else {
            selMonth.innerHTML = '<option value="">-- Seleccione un cliente primero --</option>';
            selMonth.disabled = true;
        }
        checkFormReady();
    });

    selMonth.addEventListener("change", checkFormReady);

    inputPath.addEventListener("click", async () => {
        if(window.pywebview && window.pywebview.api) {
            const dir = await window.pywebview.api.choose_directory();
            if(dir) {
                inputPath.value = dir;
                checkFormReady();
            }
        }
    });

    function checkFormReady() {
        if(selClient.value && selMonth.value && inputPath.value) {
            btnGenerateExcel.disabled = false;
        } else {
            btnGenerateExcel.disabled = true;
        }
    }

    btnGenerateExcel.addEventListener("click", async () => {
        btnGenerateExcel.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generando...';
        btnGenerateExcel.disabled = true;
        try {
            const success = await window.pywebview.api.generate_excel(
                selClient.value, selMonth.value, inputPath.value
            );
            showToast(success[1]);
        } catch (error) {
            showToast("Error al generar el Excel.");
        }
        btnGenerateExcel.innerHTML = '<i class="fa-solid fa-file-excel"></i> Generar Excel';
        btnGenerateExcel.disabled = false;
    });

    // Functions
    async function loadStats() {
        if(window.pywebview && window.pywebview.api) {
            try {
                const stats = await window.pywebview.api.get_stats();
                
                // Animate numbers
                animateValue(statProcessed, parseInt(statProcessed.textContent) || 0, stats.processed, 1000);
                animateValue(statPending, parseInt(statPending.textContent) || 0, stats.pending, 1000);
                animateValue(statOthers, parseInt(statOthers.textContent) || 0, stats.others, 1000);
                animateValue(statErrors, parseInt(statErrors.textContent) || 0, stats.errors, 1000);
                
            } catch (err) {
                console.error("Error cargando stats", err);
            }
        }
    }

    function showToast(message) {
        const toast = document.getElementById("toast");
        const toastMsg = document.getElementById("toast-msg");
        toastMsg.textContent = message;
        
        toast.classList.add("show");
        
        setTimeout(() => {
            toast.classList.remove("show");
        }, 3000);
    }

    // Number animation utility
    function animateValue(obj, start, end, duration) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = Math.floor(progress * (end - start) + start);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }
    // --- GLOBAL CONTROLS ---
    document.getElementById("btn-restart").addEventListener("click", async () => {
        if(window.pywebview && window.pywebview.api) {
            showToast("Reiniciando motor de Oculus...");
            await window.pywebview.api.restart_service();
        }
    });

    document.getElementById("btn-shutdown").addEventListener("click", async () => {
        if(window.pywebview && window.pywebview.api) {
            showToast("Apagando motor de Oculus...");
            await window.pywebview.api.shutdown_service();
        }
    });

    // --- EMAIL MANAGEMENT ---
    const btnAddEmail = document.getElementById("btn-add-email");
    const btnRefreshEmails = document.getElementById("btn-refresh-emails");
    const emailsList = document.getElementById("emails-list-container");

    document.getElementById("email-provider").addEventListener("change", (e) => {
        document.getElementById("custom-imap-group").style.display = e.target.value === "custom" ? "block" : "none";
    });

    async function loadEmails() {
        if(!window.pywebview || !window.pywebview.api) return;
        
        emailsList.innerHTML = '<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Cargando...</p></div>';
        
        try {
            const emails = await window.pywebview.api.get_emails();
            if(emails && emails.length > 0) {
                emailsList.innerHTML = '<ul class="activity-list"></ul>';
                const ul = emailsList.querySelector("ul");
                emails.forEach(em => {
                    ul.innerHTML += `
                        <li class="activity-item" style="justify-content: space-between;">
                            <div style="display: flex; gap: 12px; align-items: center;">
                                <i class="fa-solid fa-envelope teal-text"></i>
                                <div>
                                    <strong style="display:block;">${em.email}</strong>
                                    <small class="text-muted">${em.client || 'Sin cliente'} - ${em.server}</small>
                                </div>
                            </div>
                            <span class="badge ${em.active ? 'badge-teal' : 'bg-danger'}">${em.active ? 'Activo' : 'Error'}</span>
                        </li>
                    `;
                });
            } else {
                emailsList.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-solid fa-inbox"></i>
                        <p>No hay cuentas configuradas.</p>
                        <small>Usa el formulario de la izquierda para agregar la primera.</small>
                    </div>`;
            }
        } catch(e) {
            emailsList.innerHTML = '<div class="empty-state"><p>Error cargando correos.</p></div>';
        }
    }

    btnRefreshEmails.addEventListener("click", loadEmails);

    btnAddEmail.addEventListener("click", async () => {
        const client = document.getElementById("email-client-name").value;
        const email = document.getElementById("email-address").value;
        let provider = document.getElementById("email-provider").value;
        if(provider === "custom") provider = document.getElementById("custom-imap-server").value;
        const pass = document.getElementById("email-password").value;

        if(!email || !provider || !pass) {
            showToast("Complete los campos obligatorios.");
            return;
        }

        btnAddEmail.disabled = true;
        btnAddEmail.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Registrando...';

        try {
            const res = await window.pywebview.api.add_email(client, email, pass, provider);
            showToast(res[1]);
            if(res[0]) {
                document.getElementById("email-address").value = '';
                document.getElementById("email-password").value = '';
                loadEmails();
            }
        } catch(e) {
            showToast("Error de conexión con Python.");
        }

        btnAddEmail.disabled = false;
        btnAddEmail.innerHTML = '<i class="fa-solid fa-user-plus"></i> Registrar Cuenta';
    });

    // --- MANUAL REVIEW STATION ---
    let pendingReviews = [];
    let currentReviewIndex = 0;
    const btnPrevReview = document.getElementById("btn-prev-review");
    const btnNextReview = document.getElementById("btn-next-review");
    const btnSaveReview = document.getElementById("btn-save-review");
    const reviewCounter = document.getElementById("review-counter");
    const pdfEmbed = document.getElementById("pdf-embed");
    const emptyStateReview = document.getElementById("review-empty-state");

    async function loadReviews() {
        if(!window.pywebview || !window.pywebview.api) return;
        try {
            pendingReviews = await window.pywebview.api.get_manual_reviews();
            if(pendingReviews.length > 0) {
                currentReviewIndex = 0;
                emptyStateReview.style.display = 'none';
                pdfEmbed.style.display = 'block';
                updateReviewUI();
            } else {
                emptyStateReview.style.display = 'flex';
                pdfEmbed.style.display = 'none';
                reviewCounter.textContent = '0 / 0';
                btnSaveReview.disabled = true;
                btnPrevReview.disabled = true;
                btnNextReview.disabled = true;
            }
        } catch(e) {
            console.error(e);
        }
    }

    function updateReviewUI() {
        const doc = pendingReviews[currentReviewIndex];
        reviewCounter.textContent = `${currentReviewIndex + 1} / ${pendingReviews.length}`;
        
        // Navigation buttons
        btnPrevReview.disabled = currentReviewIndex === 0;
        btnNextReview.disabled = currentReviewIndex === pendingReviews.length - 1;
        btnSaveReview.disabled = false;

        // Load PDF
        pdfEmbed.src = "file:///" + doc.pdf_path; // Only works if local files are allowed, otherwise needs a python route

        // Populate fields if any were extracted with low confidence
        document.getElementById("rev-uuid").value = doc.uuid || '';
        document.getElementById("rev-control").value = doc.control || '';
        document.getElementById("rev-date").value = doc.date || '';
        document.getElementById("rev-type").value = doc.type || '03';
        document.getElementById("rev-provider-name").value = doc.provider_name || '';
        document.getElementById("rev-provider-nit").value = doc.provider_nit || '';
    }

    btnPrevReview.addEventListener("click", () => {
        if(currentReviewIndex > 0) {
            currentReviewIndex--;
            updateReviewUI();
        }
    });

    btnNextReview.addEventListener("click", () => {
        if(currentReviewIndex < pendingReviews.length - 1) {
            currentReviewIndex++;
            updateReviewUI();
        }
    });

    btnSaveReview.addEventListener("click", async () => {
        const data = {
            id: pendingReviews[currentReviewIndex].id,
            uuid: document.getElementById("rev-uuid").value,
            control: document.getElementById("rev-control").value,
            date: document.getElementById("rev-date").value,
            type: document.getElementById("rev-type").value,
            provider_name: document.getElementById("rev-provider-name").value,
            provider_nit: document.getElementById("rev-provider-nit").value
        };

        btnSaveReview.disabled = true;
        btnSaveReview.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Guardando...';

        try {
            await window.pywebview.api.save_manual_review(data);
            showToast("Datos guardados. DTE procesado.");
            // Remove from list and update
            pendingReviews.splice(currentReviewIndex, 1);
            if(currentReviewIndex >= pendingReviews.length) currentReviewIndex = Math.max(0, pendingReviews.length - 1);
            
            if(pendingReviews.length > 0) {
                updateReviewUI();
            } else {
                loadReviews(); // Refresh to show empty state properly
            }
        } catch(e) {
            showToast("Error al guardar.");
            btnSaveReview.disabled = false;
        }
        btnSaveReview.innerHTML = '<i class="fa-solid fa-save"></i> Guardar y Procesar';
    });

    // --- EXPLORER LOGIC ---
    const btnRefreshExplorer = document.getElementById("btn-refresh-explorer");
    const expFilterDate = document.getElementById("exp-filter-date");
    const expFilterClient = document.getElementById("exp-filter-client");

    if (btnRefreshExplorer) {
        btnRefreshExplorer.addEventListener("click", loadExplorer);
    }
    
    async function loadExplorer() {
        const listContainer = document.getElementById("explorer-list");
        if(!listContainer) return;

        listContainer.innerHTML = '<li class="activity-item empty-state"><p><i class="fa-solid fa-spinner fa-spin"></i> Cargando documentos...</p></li>';
        
        try {
            if(window.pywebview && window.pywebview.api) {
                const dateFilter = expFilterDate ? expFilterDate.value : "";
                const clientFilter = expFilterClient ? expFilterClient.value : "";
                const docs = await window.pywebview.api.get_other_documents(clientFilter, dateFilter);
                
                listContainer.innerHTML = '';
                if(docs.length === 0) {
                    listContainer.innerHTML = '<li class="activity-item empty-state"><p>No se encontraron documentos.</p></li>';
                    return;
                }
                
                docs.forEach(doc => {
                    const icon = doc.type === 'pdf' ? 'fa-file-pdf' : 'fa-file-code';
                    const color = doc.type === 'pdf' ? 'var(--danger)' : 'var(--warning)';
                    const li = document.createElement("li");
                    li.className = "activity-item";
                    li.innerHTML = `
                        <i class="fa-solid ${icon}" style="color: ${color}; font-size: 1.5rem;"></i>
                        <div style="flex:1;">
                            <p style="font-weight:600; font-size:0.9rem;">${doc.name}</p>
                            <span style="font-size:0.75rem; color:var(--text-muted);">${doc.client} | ${doc.date}</span>
                        </div>
                    `;
                    li.addEventListener("click", () => {
                        document.querySelectorAll("#explorer-list .activity-item").forEach(item => item.style.background = 'transparent');
                        li.style.background = 'rgba(92, 126, 143, 0.1)';
                        document.getElementById("explorer-empty-state").style.display = 'none';
                        const embed = document.getElementById("explorer-embed");
                        embed.style.display = 'block';
                        embed.src = ""; 
                        showToast(`Abriendo ${doc.name}...`);
                    });
                    listContainer.appendChild(li);
                });
            }
        } catch (e) {
            console.error(e);
            listContainer.innerHTML = '<li class="activity-item empty-state"><p>Error al cargar documentos.</p></li>';
        }
    }

    // --- SETTINGS LOGIC ---
    const btnSaveApis = document.getElementById("btn-save-apis");
    if(btnSaveApis) {
        btnSaveApis.addEventListener("click", async () => {
            const data = {
                gemini: document.getElementById("api-gemini").value,
                llama: document.getElementById("api-llama").value,
                groq: document.getElementById("api-groq").value
            };
            try {
                if(window.pywebview && window.pywebview.api) {
                    await window.pywebview.api.save_settings(data);
                    showToast("Configuración guardada exitosamente");
                }
            } catch (e) {
                showToast("Error al guardar configuración");
            }
        });
    }

    async function loadSettings() {
        try {
            if(window.pywebview && window.pywebview.api) {
                const config = await window.pywebview.api.get_settings();
                if(config.gemini) document.getElementById("api-gemini").value = config.gemini;
                if(config.llama) document.getElementById("api-llama").value = config.llama;
                if(config.groq) document.getElementById("api-groq").value = config.groq;
            }
        } catch (e) {
            console.error(e);
        }
    }

});
