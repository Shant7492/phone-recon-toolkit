document.getElementById('search-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const phone = document.getElementById('phone-input').value.trim();
    if (!phone) return;

    try {
        const response = await fetch('/api/lookup', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ number: phone })
        });
        const data = await response.json();

        if (!data.valid) {
            alert(data.error || "Invalid phone number");
            return;
        }

        renderResults(data);
    } catch (err) {
        alert("Server error: " + err.message);
    }
});

function copyToClipboard(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
        const original = btn.innerText;
        btn.innerText = "Copied!";
        setTimeout(() => { btn.innerText = original; }, 1500);
    });
}

function renderResults(data) {
    document.getElementById('results').style.display = 'block';
    document.getElementById('export-section').style.display = 'flex';

    // 1. Direct Actions
    const actionsContainer = document.getElementById('quick-actions');
    actionsContainer.innerHTML = '';
    (data.direct_actions || []).forEach(act => {
        const a = document.createElement('a');
        a.href = act.url;
        a.target = '_blank';
        a.className = 'action-btn';
        a.textContent = act.name;
        actionsContainer.appendChild(a);
    });

    // 2. Metadata (Matches old UI)
    const meta = data.metadata;
    document.getElementById('meta-e164').innerHTML = `${meta.e164} <button class="copy-btn no-print" onclick="copyToClipboard('${meta.e164}', this)">Copy</button>`;
    document.getElementById('meta-international').textContent = meta.international;
    document.getElementById('meta-national').innerHTML = `${meta.national} <button class="copy-btn no-print" onclick="copyToClipboard('${meta.national}', this)">Copy</button>`;
    document.getElementById('meta-country').textContent = meta.country_code ? `+${meta.country_code}` : 'Unknown';
    document.getElementById('meta-carrier').textContent = meta.carrier;
    document.getElementById('meta-circle').textContent = meta.circle;
    document.getElementById('meta-tz').textContent = (meta.timezones || []).join(', ');

    // 3. Risk Heuristics (Matches old UI)
    const risk = data.risk;
    const riskDisplay = document.getElementById('risk-score-display');
    riskDisplay.textContent = `${risk.score}/100 ${risk.level}`;
    riskDisplay.style.color = risk.level === 'HIGH' ? '#dc2626' : (risk.level === 'MEDIUM' ? '#d97706' : '#16a34a');
    
    const riskNotes = document.getElementById('risk-notes');
    riskNotes.innerHTML = '';
    if (risk.reasons && risk.reasons.length > 0) {
        risk.reasons.forEach(r => {
            const li = document.createElement('li');
            li.textContent = r;
            riskNotes.appendChild(li);
        });
    } else {
        const li = document.createElement('li');
        li.textContent = "Standard profile, no abnormal flags detected.";
        riskNotes.appendChild(li);
    }

    // 4. Dorks (Restored Collapsible UI)
    const dorksContainer = document.getElementById('dorks-container');
    dorksContainer.innerHTML = '';
    (data.dorks || []).forEach((cat, index) => {
        const details = document.createElement('details');
        if (index === 0) details.open = true; // Open the first section by default
        
        const summary = document.createElement('summary');
        summary.textContent = cat.category;
        details.appendChild(summary);

        cat.queries.forEach(q => {
            const box = document.createElement('div');
            box.className = 'query-box';
            
            box.innerHTML = `
                <div style="font-size: 12px; margin-bottom: 4px;">${q.title}</div>
                <div class="query-text">
                    <span>${q.query}</span>
                    <button class="copy-btn no-print" onclick="copyToClipboard('${q.query.replace(/'/g, "\\'")}', this)">Copy</button>
                </div>
                <div class="query-links no-print">
                    <a href="${q.urls.Google}" target="_blank">Google</a>
                    <a href="${q.urls.DuckDuckGo}" target="_blank">DuckDuckGo</a>
                    <a href="${q.urls.Bing}" target="_blank">Bing</a>
                </div>
            `;
            details.appendChild(box);
        });
        
        dorksContainer.appendChild(details);
    });
}
