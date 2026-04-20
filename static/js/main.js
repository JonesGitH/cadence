function openModal(id) {
  document.getElementById(id).classList.add('open');
}
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}

document.addEventListener('click', function(e) {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
  }
});

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
  }
});

document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.alert').forEach(function(el) {
    setTimeout(function() {
      el.style.transition = 'opacity .4s';
      el.style.opacity = '0';
      setTimeout(function() { el.remove(); }, 400);
    }, 6000);
  });
});


function confirmDelete(formId, label) {
  var modal  = document.getElementById('delete-confirm-modal');
  var msgEl  = document.getElementById('delete-confirm-msg');
  var btn    = document.getElementById('delete-confirm-btn');
  if (msgEl) msgEl.textContent = label ? 'Delete ' + label + '?' : 'Are you sure you want to delete this?';
  if (btn) {
    btn.onclick = function() {
      document.getElementById(formId).submit();
    };
  }
  if (modal) modal.classList.add('open');
}

/* ── Invoice creation flow ──────────────────────────────────────────────────── */
(function() {
  var fetchBtn        = document.getElementById('fetch-btn');
  var generateBtn     = document.getElementById('generate-btn');
  var sessionsArea    = document.getElementById('sessions-area');
  var sessionsBody    = document.getElementById('sessions-body');
  var sessionsSummary = document.getElementById('sessions-summary');
  var noSessionsMsg   = document.getElementById('no-sessions-msg');
  var loadingEl       = document.getElementById('fetch-loading');
  var fetchError      = document.getElementById('fetch-error');
  var lateFeeBtn      = document.getElementById('late-fee-btn');
  var lateFeeApplyBtn = document.getElementById('late-fee-apply-btn');
  var creditBtn       = document.getElementById('credit-btn');
  var creditApplyBtn  = document.getElementById('credit-apply-btn');

  if (!fetchBtn) return;

  var fetchedSessions = [];
  var currentRate     = 0;
  var lateFee         = null; // {amount, note} or null
  var credit          = null; // {amount, note} or null

  function showFetchError(msg) {
    if (fetchError) {
      fetchError.textContent = msg;
      fetchError.style.display = 'block';
    }
  }

  function updateAdjustmentBtn(btn, item, defaultLabel) {
    if (!btn) return;
    if (item) {
      btn.textContent = defaultLabel + ': $' + item.amount.toFixed(2) + ' ✎';
      btn.classList.add('btn-warning');
    } else {
      btn.textContent = defaultLabel;
      btn.classList.remove('btn-warning');
    }
  }

  function updateSummary(sessions, rate) {
    var checks   = sessionsBody.querySelectorAll('.session-check');
    var selected = [];
    checks.forEach(function(cb) {
      if (cb.checked) selected.push(sessions[parseInt(cb.dataset.idx)]);
    });
    var totalHrs = selected.reduce(function(sum, s) { return sum + s.duration_hours; }, 0);
    var totalAmt = selected.reduce(function(sum, s) { return sum + s.line_total; }, 0);
    if (lateFee) totalAmt += lateFee.amount;
    if (credit)  totalAmt -= credit.amount;
    if (sessionsSummary) {
      sessionsSummary.textContent =
        selected.length + ' session(s) selected — ' +
        totalHrs.toFixed(2) + ' hrs — Total: $' + totalAmt.toFixed(2);
    }
    generateBtn.disabled = selected.length === 0;
  }

  function makeAdjustmentRow(label, item, colorClass, removeId, isCredit) {
    var tr = document.createElement('tr');
    tr.className = 'session-row';
    var descCell = document.createElement('td');
    descCell.colSpan = 4;
    descCell.style.cssText = 'font-style:italic; color:var(--muted)';
    var descText = document.createTextNode(label + (item.note ? ': ' + item.note : ''));
    var removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn ' + colorClass + ' btn-sm';
    removeBtn.id = removeId;
    removeBtn.style.cssText = 'font-size:11px;padding:1px 7px;margin-left:8px';
    removeBtn.textContent = 'Remove';
    descCell.appendChild(descText);
    descCell.appendChild(removeBtn);
    var emptyCell = document.createElement('td');
    var amtCell = document.createElement('td');
    amtCell.className = 'text-right';
    amtCell.textContent = (isCredit ? '-' : '') + '$' + item.amount.toFixed(2);
    tr.appendChild(emptyCell);
    tr.appendChild(descCell);
    tr.appendChild(amtCell);
    return tr;
  }

  function removeLateFeeRow() {
    lateFee = null;
    updateAdjustmentBtn(lateFeeBtn, lateFee, 'Add Late Fee');
    renderSessions(fetchedSessions, currentRate);
  }

  function removeCreditRow() {
    credit = null;
    updateAdjustmentBtn(creditBtn, credit, 'Add Credit');
    renderSessions(fetchedSessions, currentRate);
  }

  var selectAllChk = document.getElementById('select-all-sessions');
  if (selectAllChk) {
    selectAllChk.addEventListener('change', function() {
      sessionsBody.querySelectorAll('.session-check').forEach(function(cb) {
        cb.checked = selectAllChk.checked;
      });
      updateSummary(fetchedSessions, currentRate);
    });
  }

  function renderSessions(sessions, rate) {
    sessionsBody.innerHTML = '';
    if (selectAllChk) selectAllChk.checked = true;

    if (sessions.length === 0 && !lateFee && !credit) {
      noSessionsMsg.style.display = 'block';
      generateBtn.disabled = true;
      sessionsSummary.textContent = '';
      return;
    }

    noSessionsMsg.style.display = 'none';
    generateBtn.disabled = false;

    sessions.forEach(function(s, i) {
      var tr = document.createElement('tr');
      tr.className = 'session-row';
      tr.innerHTML =
        '<td><input type="checkbox" class="session-check" checked data-idx="' + i + '"></td>' +
        '<td>' + s.date_display + '</td>' +
        '<td>' + s.start_time + ' – ' + s.end_time + '</td>' +
        '<td class="text-right">' + s.duration_hours.toFixed(2) + ' hrs</td>' +
        '<td class="text-right">$' + rate.toFixed(2) + '/session</td>' +
        '<td class="text-right">$' + s.line_total.toFixed(2) + '</td>';
      sessionsBody.appendChild(tr);
    });

    if (lateFee) {
      var tr = makeAdjustmentRow('Late Fee', lateFee, 'btn-danger', 'remove-late-fee', false);
      sessionsBody.appendChild(tr);
      document.getElementById('remove-late-fee').addEventListener('click', removeLateFeeRow);
    }

    if (credit) {
      var tr = makeAdjustmentRow('Credit', credit, 'btn-danger', 'remove-credit', true);
      sessionsBody.appendChild(tr);
      document.getElementById('remove-credit').addEventListener('click', removeCreditRow);
    }

    updateSummary(sessions, rate);
    sessionsBody.onchange = function() {
      updateSummary(sessions, rate);
      if (selectAllChk) {
        var checks = sessionsBody.querySelectorAll('.session-check');
        var allChecked = Array.from(checks).every(function(cb) { return cb.checked; });
        selectAllChk.checked = allChecked;
      }
    };
  }

  function wireAdjustmentModal(openBtn, applyBtn, modalId, amountInputId, noteInputId, errId, getItem, setItem, updateBtn, label) {
    if (openBtn) {
      openBtn.addEventListener('click', function() {
        var item = getItem();
        document.getElementById(amountInputId).value = item ? item.amount : '';
        document.getElementById(noteInputId).value   = item ? item.note   : '';
        document.getElementById(errId).style.display = 'none';
        openModal(modalId);
      });
    }
    if (applyBtn) {
      applyBtn.addEventListener('click', function() {
        var amountInput = document.getElementById(amountInputId);
        var amount      = parseFloat(amountInput.value);
        var errEl       = document.getElementById(errId);
        if (isNaN(amount) || amount <= 0) {
          errEl.style.display = 'block';
          amountInput.focus();
          return;
        }
        errEl.style.display = 'none';
        setItem({
          amount: Math.round(amount * 100) / 100,
          note:   document.getElementById(noteInputId).value.trim(),
        });
        closeModal(modalId);
        updateBtn();
        renderSessions(fetchedSessions, currentRate);
      });
    }
  }

  wireAdjustmentModal(
    lateFeeBtn, lateFeeApplyBtn, 'late-fee-modal',
    'late-fee-amount', 'late-fee-note', 'late-fee-amount-err',
    function() { return lateFee; },
    function(v) { lateFee = v; },
    function() { updateAdjustmentBtn(lateFeeBtn, lateFee, 'Add Late Fee'); },
    'Add Late Fee'
  );

  wireAdjustmentModal(
    creditBtn, creditApplyBtn, 'credit-modal',
    'credit-amount', 'credit-note', 'credit-amount-err',
    function() { return credit; },
    function(v) { credit = v; },
    function() { updateAdjustmentBtn(creditBtn, credit, 'Add Credit'); },
    'Add Credit'
  );

  var sessionsHint = document.getElementById('sessions-hint');
  var refetchBtn   = document.getElementById('refetch-btn');

  function resetSessionsArea() {
    sessionsArea.classList.remove('visible');
    if (sessionsHint) sessionsHint.style.display = '';
  }

  if (refetchBtn) refetchBtn.addEventListener('click', resetSessionsArea);

  fetchBtn.addEventListener('click', function() {
    var clientId = document.getElementById('client-select').value;
    var month    = document.getElementById('month-select').value;
    var year     = document.getElementById('year-select').value;

    if (!clientId) { showFetchError('Please select a client.'); return; }

    fetchBtn.disabled = true;
    loadingEl.style.display = 'inline-block';
    if (fetchError) fetchError.style.display = 'none';
    sessionsArea.classList.remove('visible');

    fetch('/invoices/fetch-sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id: clientId, month: month, year: year })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      fetchBtn.disabled = false;
      loadingEl.style.display = 'none';
      if (data.error) { showFetchError(data.error); return; }
      fetchedSessions = data.sessions;
      currentRate     = data.rate;
      renderSessions(data.sessions, data.rate);
      sessionsArea.classList.add('visible');
      if (sessionsHint) sessionsHint.style.display = 'none';
    })
    .catch(function() {
      fetchBtn.disabled = false;
      loadingEl.style.display = 'none';
      showFetchError('Could not reach Microsoft 365. Check your connection in Settings.');
    });
  });

  function resetGenerateBtn() {
    generateBtn.disabled = false;
    generateBtn.innerHTML =
      '<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' +
      '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>' +
      '<polyline points="14 2 14 8 20 8"/></svg> Generate Invoice &amp; Save PDF';
  }

  function doGenerate(force) {
    var clientId = document.getElementById('client-select').value;
    var month    = document.getElementById('month-select').value;
    var year     = document.getElementById('year-select').value;

    var checks   = sessionsBody.querySelectorAll('.session-check');
    var selected = [];
    checks.forEach(function(cb) {
      if (cb.checked) selected.push(fetchedSessions[parseInt(cb.dataset.idx)]);
    });

    if (selected.length === 0) return;

    generateBtn.disabled = true;
    generateBtn.textContent = 'Generating…';

    fetch('/invoices/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id: clientId, month: month, year: year, sessions: selected, late_fee: lateFee, credit: credit, force: force })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.duplicate) {
        resetGenerateBtn();
        if (confirm(
          'An invoice (' + data.existing_number + ') already exists for this client and month.\n\n' +
          'Generate another one anyway?'
        )) {
          doGenerate(true);
        }
        return;
      }
      if (data.error) {
        showFetchError(data.error);
        resetGenerateBtn();
        return;
      }
      window.location.href = '/invoices/' + data.invoice_id;
    })
    .catch(function() {
      showFetchError('An error occurred generating the invoice.');
      resetGenerateBtn();
    });
  }

  generateBtn && generateBtn.addEventListener('click', function() { doGenerate(false); });
})();

var _EMAIL_BTN_HTML = '<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg> Send via Email';

function sendEmail(invoiceId) {
  var btn = event.currentTarget;
  btn.disabled = true;
  btn.textContent = 'Sending…';
  fetch('/invoices/' + invoiceId + '/send-email', { method: 'POST' })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      btn.disabled = false;
      btn.innerHTML = _EMAIL_BTN_HTML;
      if (d.error) Toast.show(d.error, 'error');
      else Toast.show('Invoice email sent.', 'success');
    })
    .catch(function() {
      btn.disabled = false;
      btn.innerHTML = _EMAIL_BTN_HTML;
      Toast.show('Could not send email. Check Microsoft 365 in Settings.', 'error');
    });
}

(function() {
  var connectBtn = document.getElementById('graph-connect-btn');
  if (!connectBtn) return;

  var modal      = document.getElementById('graph-auth-modal');
  var urlEl      = document.getElementById('graph-auth-url');
  var codeEl     = document.getElementById('graph-auth-code');
  var statusEl   = document.getElementById('graph-auth-status');
  var pollTimer  = null;

  connectBtn.addEventListener('click', function() {
    connectBtn.disabled = true;
    connectBtn.textContent = 'Starting…';
    fetch('/settings/graph/connect', { method: 'POST' })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        connectBtn.disabled = false;
        connectBtn.textContent = 'Connect Microsoft 365';
        if (d.error) { alert(d.error); return; }
        urlEl.href        = d.verification_url;
        urlEl.textContent = d.verification_url;
        codeEl.textContent = d.user_code;
        statusEl.textContent = 'Waiting for sign-in…';
        if (modal) modal.classList.add('open');
        window.open(d.verification_url, '_blank');
        pollTimer = setInterval(function() {
          fetch('/settings/graph/poll')
            .then(function(r) { return r.json(); })
            .then(function(p) {
              if (p.done) {
                clearInterval(pollTimer);
                if (modal) modal.classList.remove('open');
                window.location.reload();
              } else if (p.error) {
                clearInterval(pollTimer);
                statusEl.textContent = 'Error: ' + p.error;
              }
            });
        }, 2500);
      })
      .catch(function() {
        connectBtn.disabled = false;
        connectBtn.textContent = 'Connect Microsoft 365';
        alert('Could not start authentication.');
      });
  });
})();

function togglePaid(invoiceId) {
  var btn = document.getElementById('paid-btn');
  btn.disabled = true;
  fetch('/invoices/' + invoiceId + '/toggle-paid', { method: 'POST' })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      btn.disabled = false;
      if (d.error) { Toast.show(d.error, 'error'); return; }
      if (d.paid) {
        btn.textContent = '✓ Paid';
        btn.className = 'btn btn-success';
        Toast.show('Marked as paid.', 'success');
      } else {
        btn.textContent = 'Mark as Paid';
        btn.className = 'btn btn-ghost';
        Toast.show('Marked as unpaid.', 'info');
      }
    })
    .catch(function() { btn.disabled = false; Toast.show('Could not update payment status.', 'error'); });
}

(function() {
  var filterClient = document.getElementById('filter-client');
  var filterYear   = document.getElementById('filter-year');
  var filterStatus = document.getElementById('filter-status');
  var countEl      = document.getElementById('filter-count');
  if (!filterClient) return;

  var tbody     = document.getElementById('invoice-tbody');
  var noRow     = document.getElementById('no-inv-results');
  var clearBtn  = document.getElementById('filter-clear-btn');
  var allRows   = Array.from(tbody.querySelectorAll('tr[data-client]'));

  function isFiltered() {
    return filterClient.value || filterYear.value || filterStatus.value;
  }

  function applyFilters() {
    var client = filterClient.value;
    var year   = filterYear.value;
    var status = filterStatus.value;
    var visible = 0;
    allRows.forEach(function(row) {
      var show = (!client || row.dataset.client === client) &&
                 (!year   || row.dataset.year   === year)   &&
                 (!status || row.dataset.status  === status);
      row.style.display = show ? '' : 'none';
      if (show) visible++;
    });
    if (noRow) noRow.style.display = (visible === 0) ? '' : 'none';
    if (countEl) countEl.textContent = isFiltered() ? visible + ' of ' + allRows.length + ' invoices' : '';
    if (clearBtn) clearBtn.style.display = isFiltered() ? '' : 'none';
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', function() {
      filterClient.value = '';
      filterYear.value   = '';
      filterStatus.value = '';
      applyFilters();
    });
  }

  filterClient.addEventListener('change', applyFilters);
  filterYear.addEventListener('change',   applyFilters);
  filterStatus.addEventListener('change', applyFilters);
})();

function openPdf(invoiceId) {
  fetch('/invoices/' + invoiceId + '/open-pdf', { method: 'POST' })
    .then(function(r) { return r.json(); })
    .then(function(d) { if (d.error) Toast.show(d.error, 'error'); })
    .catch(function() { Toast.show('Could not open PDF.', 'error'); });
}

function openFolder(invoiceId) {
  fetch('/invoices/' + invoiceId + '/open-folder', { method: 'POST' })
    .then(function(r) { return r.json(); })
    .then(function(d) { if (d.error) Toast.show(d.error, 'error'); })
    .catch(function() { Toast.show('Could not open folder.', 'error'); });
}

(function() {
  var searchInput = document.getElementById('student-search');
  var clearBtn    = document.getElementById('search-clear-btn');
  if (!searchInput) return;

  var rows       = document.querySelectorAll('tbody tr[data-search]');
  var noResults  = document.getElementById('no-results-row');

  function filter(q) {
    var term = q.trim().toLowerCase();
    var visible = 0;
    rows.forEach(function(row) {
      var match = !term || row.dataset.search.indexOf(term) !== -1;
      row.style.display = match ? '' : 'none';
      if (match) visible++;
    });
    if (noResults) noResults.style.display = (visible === 0 && term) ? '' : 'none';
    if (clearBtn)  clearBtn.style.display  = term ? 'inline' : 'none';
  }

  searchInput.addEventListener('input', function() { filter(this.value); });
  if (clearBtn) {
    clearBtn.addEventListener('click', function() {
      searchInput.value = '';
      filter('');
      searchInput.focus();
    });
  }
})();

(function() {
  var defaultRadios = document.querySelectorAll('.cal-default-radio');
  if (!defaultRadios.length) return;
  defaultRadios.forEach(function(radio) {
    radio.addEventListener('change', function() {
      defaultRadios.forEach(function(r) { if (r !== radio) r.checked = false; });
    });
  });
})();

/* ── Toast system ───────────────────────────────────────────────────────────── */
window.Toast = (function() {
  function stack() {
    var s = document.getElementById('toast-stack');
    if (!s) {
      s = document.createElement('div');
      s.id = 'toast-stack';
      s.className = 'toast-stack';
      document.body.appendChild(s);
    }
    return s;
  }
  function show(msg, type, ms) {
    type = type || 'info';
    ms = ms || 3400;
    var t = document.createElement('div');
    t.className = 'toast toast-' + type;
    t.textContent = msg;
    stack().appendChild(t);
    setTimeout(function() {
      t.style.animation = 'toast-out .25s ease-in forwards';
      setTimeout(function() { if (t.parentNode) t.parentNode.removeChild(t); }, 250);
    }, ms);
    return t;
  }
  return { show: show };
})();

/* ── Sidebar toggle (mobile) ────────────────────────────────────────────────── */
(function() {
  document.addEventListener('click', function(e) {
    var toggle = e.target.closest('.sidebar-toggle');
    var sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;
    if (toggle) {
      sidebar.classList.toggle('open');
      return;
    }
    // close when clicking main content on small screens
    if (sidebar.classList.contains('open') && !e.target.closest('.sidebar')) {
      sidebar.classList.remove('open');
    }
  });
})();

/* ── Sortable tables ────────────────────────────────────────────────────────── */
(function() {
  function sortKey(td, type) {
    if (!td) return type === 'number' ? 0 : '';
    var v = td.getAttribute('data-sort-value');
    if (v === null) v = td.textContent.trim();
    if (type === 'number') {
      var n = parseFloat(v.replace(/[^0-9.\-]/g, ''));
      return isNaN(n) ? 0 : n;
    }
    return v.toLowerCase();
  }
  document.querySelectorAll('table').forEach(function(table) {
    var headers = table.querySelectorAll('th.sortable');
    if (!headers.length) return;
    headers.forEach(function(th, idx) {
      th.addEventListener('click', function() {
        var type = th.getAttribute('data-sort-type') || 'string';
        var asc = !th.classList.contains('sort-asc');
        headers.forEach(function(h) { h.classList.remove('sort-asc', 'sort-desc'); });
        th.classList.add(asc ? 'sort-asc' : 'sort-desc');
        var tbody = table.querySelector('tbody');
        if (!tbody) return;
        var rows = Array.from(tbody.querySelectorAll('tr')).filter(function(r) {
          return !r.hasAttribute('data-no-sort');
        });
        rows.sort(function(a, b) {
          var av = sortKey(a.children[idx], type);
          var bv = sortKey(b.children[idx], type);
          if (av < bv) return asc ? -1 : 1;
          if (av > bv) return asc ? 1 : -1;
          return 0;
        });
        rows.forEach(function(r) { tbody.appendChild(r); });
      });
    });
  });
})();

/* ── Row action menus ───────────────────────────────────────────────────────── */
(function() {
  document.addEventListener('click', function(e) {
    var btn = e.target.closest('.row-actions-btn');
    if (btn) {
      e.stopPropagation();
      var wrap = btn.closest('.row-actions');
      var wasOpen = wrap.classList.contains('open');
      document.querySelectorAll('.row-actions.open').forEach(function(w) {
        w.classList.remove('open');
        var m = w.querySelector('.row-actions-menu');
        if (m) m.style.cssText = '';
      });
      if (!wasOpen) {
        wrap.classList.add('open');
        var menu = wrap.querySelector('.row-actions-menu');
        if (menu) {
          var r = btn.getBoundingClientRect();
          menu.style.position = 'fixed';
          menu.style.top = (r.bottom + 4) + 'px';
          menu.style.right = (window.innerWidth - r.right) + 'px';
          menu.style.left = 'auto';
          // flip up if not enough space below
          var mh = menu.offsetHeight;
          if (r.bottom + 4 + mh > window.innerHeight - 8) {
            menu.style.top = (r.top - 4 - mh) + 'px';
          }
        }
      }
      return;
    }
    if (!e.target.closest('.row-actions-menu')) {
      document.querySelectorAll('.row-actions.open').forEach(function(w) { w.classList.remove('open'); });
    }
  });
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.row-actions.open').forEach(function(w) { w.classList.remove('open'); });
    }
  });
})();

/* ── Tabs ───────────────────────────────────────────────────────────────────── */
(function() {
  document.querySelectorAll('.tabs').forEach(function(group) {
    var tabs = group.querySelectorAll('[data-tab-target]');
    if (!tabs.length) return;
    tabs.forEach(function(tab) {
      tab.addEventListener('click', function() {
        var target = tab.getAttribute('data-tab-target');
        tabs.forEach(function(t) { t.classList.toggle('active', t === tab); });
        document.querySelectorAll('.tab-panel').forEach(function(p) {
          p.classList.toggle('active', p.id === target);
        });
      });
    });
  });
})();
