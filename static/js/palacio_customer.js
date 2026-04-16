console.log("customer js loaded!")

const API_BASE_URL = `${window.location.origin}/api`;

let packageCatalog = [];
let currentCalendarDate = new Date();
let selectedCalendarDate = null;
let reviewChart = null;

function initReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '0px 0px -40px 0px'
  });

  document.querySelectorAll('.reveal, .reveal-left, .reveal-right').forEach((el) => {
    observer.observe(el);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initReveal();
  loadCustomerPackages();
});

function gotoPage(pageId, anchorId = null) {
  document.querySelectorAll('.page').forEach((p) => p.classList.remove('active'));
  const page = document.getElementById(pageId);
  if (!page) return;
  page.classList.add('active');
  window.scrollTo({ top: 0, behavior: 'auto' });
  if (anchorId) {
    const el = document.getElementById(anchorId);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  }
  initReveal();
}

document.addEventListener('click', (e) => {
  const trigger = e.target.closest('[data-goto]');
  if (trigger) {
    e.preventDefault();
    gotoPage(trigger.dataset.goto, trigger.dataset.anchor || null);
    return;
  }

const leftBtn = document.querySelector('.arrow-left');
const rightBtn = document.querySelector('.arrow-right');
const rulesEl = document.querySelector('.rulesyan');

if (leftBtn && rightBtn && rulesEl) {
  leftBtn.addEventListener('click', () => {
    rulesEl.scrollBy({ left: -330, behavior: 'smooth' });
  });

  rightBtn.addEventListener('click', () => {
    rulesEl.scrollBy({ left: 330, behavior: 'smooth' });
  });
}

  const anchor = e.target.closest('a[href^="#"]');
  if (anchor) {
    const id = anchor.getAttribute('href').slice(1);
    const target = document.getElementById(id);
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth' });
    }
  }
});

function initHamburger(hamburgerId, navLinksId) {
  const hamburger = document.getElementById(hamburgerId);
  const navLinks = document.getElementById(navLinksId);
  if (!hamburger || !navLinks) return;
  hamburger.addEventListener('click', () => {
    hamburger.classList.toggle('open');
    navLinks.classList.toggle('nav-open');
  });
}


function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

async function api(path, options = {}) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const response = await fetch(`${API_BASE_URL}${normalizedPath}`, options);
  let payload = null;
  try {
    payload = await response.json();
  } catch (err) {
    payload = null;
  }

  if (!response.ok) {
    throw new Error(payload?.message || `Request failed with status ${response.status}`);
  }

  return payload?.data ?? payload;
}

function showToast(id, message) {
  const toast = document.getElementById(id);
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2800);
}

function populateAccommodationOptions() {
  const select = document.getElementById('accomSelect');
  if (!select) return;

  select.innerHTML = '<option disabled selected value="">— Select Package —</option>' +
    packageCatalog.map((pkg) => `<option value="${pkg.id}">${escapeHtml(pkg.name || 'Package')} · up to ${pkg.pax_included ?? pkg.included_pax ?? 0} pax</option>`).join('');
}

function formatPeso(value) {
  return `₱ ${Number(value || 0).toLocaleString('en-PH', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })}`;
}

function setFieldError(el, message = 'Required input') {
  if (!el) return false;
  el.classList.add('input-error');
  el.dataset.error = message;
  let note = el.parentElement?.querySelector('.field-error');
  if (!note) {
    note = document.createElement('div');
    note.className = 'field-error';
    el.parentElement?.appendChild(note);
  }
  note.textContent = message;
  return false;
}

function clearFieldError(el) {
  if (!el) return;
  el.classList.remove('input-error');
  const note = el.parentElement?.querySelector('.field-error');
  if (note) note.remove();
}

function validateRequiredField(el, message = 'Required input') {
  if (!el) return false;
  const isCheckbox = el.type === 'checkbox';
  const isFile = el.type === 'file';
  const value = isCheckbox ? el.checked : isFile ? el.files?.length : String(el.value || '').trim();
  if (!value) return setFieldError(el, message);
  clearFieldError(el);
  return true;
}

function selectedPackage() {
  const pkgId = Number(document.getElementById('accomSelect')?.value || 0);
  return packageCatalog.find((pkg) => Number(pkg.id) === pkgId) || null;
}

function selectedBookingType(pkg) {
  return (pkg?.booking_type || '').toLowerCase() || 'dayswimming';
}

function scheduleLabelFromResponse(data) {
  return `${data.check_in_time || '--'} to ${data.check_out_time || '--'}`;
}

function applyPackageTimeSlot(pkg) {
  const timeSelect = document.getElementById('timeSelect');
  if (!timeSelect) return;
  const slot = pkg?.time_slot || '— Auto-filled from package —';
  timeSelect.innerHTML = `<option value="${slot}" selected>${slot}</option>`;
}

function validatePaxAgainstPackage(showMessage = true) {
  const adultsEl = document.getElementById('adults');
  const childrenEl = document.getElementById('children');
  const pkg = selectedPackage();
  if (!pkg) return true;
  const totalPax = Number(adultsEl?.value || 0) + Number(childrenEl?.value || 0);
  const maxPax = Number(pkg.pax_included ?? pkg.included_pax ?? 0);
  if (maxPax && totalPax > maxPax) {
    if (showMessage) {
      setFieldError(adultsEl, `Too much for pax. Maximum for this package is ${maxPax}.`);
      setFieldError(childrenEl, `Too much for pax. Maximum for this package is ${maxPax}.`);
    }
    return false;
  }
  clearFieldError(adultsEl);
  clearFieldError(childrenEl);
  return true;
}

function getPackageIcon(timeSlot = '') {
  const normalized = String(timeSlot).toLowerCase();
  if (normalized.includes('6:00 am to 5:00 pm')) return '🌤️';
  if (normalized.includes('6:00 pm to 5:00 am')) return '🌙';
  if (normalized.includes('6:00 am to 5:00 am')) return '🏡';
  return '⭐';
}

async function loadCustomerPackages() {
  try {
    const data = await api('/packages');
    packageCatalog = Array.isArray(data) ? data : [];

    const container = document.getElementById('customerPackagesContainer');
    if (container) {
      container.innerHTML = packageCatalog.length ? packageCatalog.map((pkg, index) => {
        const normalizedType = selectedBookingType(pkg);
        const isFeatured = normalizedType === 'nightswimming';
        const pax = Number(pkg.pax_included ?? pkg.included_pax ?? 0);
        const inclusions = escapeHtml(pkg.inclusion || pkg.description || 'Unlimited Pool Access');
        const weekdayPrice = formatPeso(pkg.weekday_price ?? pkg.base_price ?? 0);
        const weekendPrice = formatPeso(pkg.weekend_price ?? pkg.holiday_price ?? pkg.base_price ?? 0);
        return `
          <div class="rate-card ${isFeatured ? 'featured' : ''} reveal reveal-delay-${(index % 3) + 1}">
            <div class="rate-icon">${escapeHtml(pkg.icon || getPackageIcon(pkg.time_slot))}</div>
            <h3>${escapeHtml(pkg.name || 'Package')}</h3>
            <div class="rate-pax">UP TO ${pax || 20} GUESTS</div>
            <div class="rate-divider"></div>
            <div class="rate-label">WEEKDAYS</div>
            <div class="rate-price">${weekdayPrice}</div>
            <div class="rate-label">WEEKENDS &amp; HOLIDAYS</div>
            <div class="rate-price secondary">${weekendPrice}</div>
            <div class="rate-divider"></div>
            <div class="rate-inclusion">${inclusions}</div>
            <div class="rate-note">${escapeHtml(pkg.time_slot || '')}</div>
          </div>
        `;
      }).join('') : '<p>No packages available right now.</p>';
    }

    populateAccommodationOptions();
  } catch (err) {
    console.warn('Failed to load packages:', err.message);
  }
}

async function loadPackages() {
  try {
    packageCatalog = await api('/packages');
    populateAccommodationOptions();
  } catch (err) {
    console.warn('Failed to load packages:', err.message);
    packageCatalog = [];
    populateAccommodationOptions();
  }
}

async function updatePrice() {
  const priceOutput = document.getElementById('priceOutput');
  const priceRange = document.getElementById('priceRange');
  const checkIn = document.getElementById('checkIn')?.value;
  const adults = Number(document.getElementById('adults')?.value || 0);
  const children = Number(document.getElementById('children')?.value || 0);
  const pkg = selectedPackage();
  const bookingType = selectedBookingType(pkg);

  applyPackageTimeSlot(pkg);
  validatePaxAgainstPackage(false);

  if (!priceOutput) return;
  if (!checkIn || !pkg || adults < 1) {
    priceOutput.innerHTML = '<strong>Total:</strong> ₱0<br><strong>Schedule:</strong> --<br><strong>Required Downpayment:</strong> ₱2,000';
    if (priceRange) priceRange.value = 0;
    return;
  }

  try {
    const data = await api(`/bookings/price?booking_type=${encodeURIComponent(bookingType)}&check_in_date=${encodeURIComponent(checkIn)}&adults=${adults}&youth=${children}&package_id=${pkg.id}`);
    const total = Number(data.total_price || 0);
    priceOutput.innerHTML = `<strong>Total:</strong> ${formatPeso(total)}<br><strong>Schedule:</strong> ${scheduleLabelFromResponse(data)}<br><strong>Required Downpayment:</strong> ₱2,000`;
    if (priceRange) {
      priceRange.max = Math.max(total, 35000);
      priceRange.value = total;
    }
  } catch (err) {
    priceOutput.innerHTML = `<strong>Total:</strong> ₱0<br><strong>Schedule:</strong> --<br><span style="color:#c62828;">${err.message}</span>`;
  }
}

async function submitBooking() {
  const firstNameEl = document.getElementById('firstName');
  const lastNameEl = document.getElementById('lastName');
  const emailEl = document.getElementById('emailAddr');
  const phoneEl = document.getElementById('phoneNum');
  const checkInEl = document.getElementById('checkIn');
  const adultsEl = document.getElementById('adults');
  const childrenEl = document.getElementById('children');
  const packageEl = document.getElementById('accomSelect');
  const validIdEl = document.getElementById('validID');
  const termsEl = document.getElementById('termscondition');
  const cancelEl = document.getElementById('cancelpolicy');
  const paymentMethod = document.querySelector('input[name="bayadmethod"]:checked')?.value || '';
  const pkg = selectedPackage();

  let valid = true;
  [firstNameEl, lastNameEl, emailEl, phoneEl, checkInEl, adultsEl, packageEl, validIdEl].forEach((el) => {
    if (!validateRequiredField(el)) valid = false;
  });
  if (!paymentMethod) valid = setFieldError(document.getElementById('cash'), 'Required input') && valid;
  if (!validateRequiredField(termsEl, 'Required input')) valid = false;
  if (!validateRequiredField(cancelEl, 'Required input')) valid = false;
  if (!validatePaxAgainstPackage(true)) valid = false;
  if (!pkg) valid = false;

  let accountName = '';
  let paymentNumber = '';
  let screenshot = null;
  if (paymentMethod === 'gcash') {
    accountName = document.getElementById('gcashName')?.value.trim() || '';
    paymentNumber = document.getElementById('gcashNum')?.value.trim() || '';
    screenshot = document.getElementById('gcashScreenshot')?.files?.[0] || null;
    if (!validateRequiredField(document.getElementById('gcashName'))) valid = false;
    if (!validateRequiredField(document.getElementById('gcashNum'))) valid = false;
    if (!validateRequiredField(document.getElementById('gcashScreenshot'))) valid = false;
  } else if (paymentMethod === 'paymaya') {
    accountName = document.getElementById('cardHolder')?.value.trim() || '';
    paymentNumber = document.getElementById('cardNumber')?.value.trim() || '';
    screenshot = document.getElementById('txnScreenshot')?.files?.[0] || null;
    if (!validateRequiredField(document.getElementById('cardHolder'))) valid = false;
    if (!validateRequiredField(document.getElementById('cardNumber'))) valid = false;
    if (!validateRequiredField(document.getElementById('txnScreenshot'))) valid = false;
  }

  if (!valid) {
    alert('Please complete the required fields marked in red.');
    return;
  }

  const formData = new FormData();
  formData.append('first_name', firstNameEl.value.trim());
  formData.append('last_name', lastNameEl.value.trim());
  formData.append('email', emailEl.value.trim());
  formData.append('phone', phoneEl.value.trim());
  formData.append('booking_type', selectedBookingType(pkg));
  formData.append('check_in_date', checkInEl.value);
  formData.append('adults', adultsEl.value || '1');
  formData.append('youth', childrenEl.value || '0');
  formData.append('package_id', packageEl.value);
  formData.append('payment_method', paymentMethod);
  formData.append('downpayment', '2000');
  formData.append('payment_ref', accountName);
  formData.append('payment_number', paymentNumber);
  formData.append('special_request', document.getElementById('specialRequest')?.value.trim() || '');
  formData.append('valid_id', validIdEl.files[0]);
  if (screenshot) formData.append('payment_screenshot', screenshot);

  try {
    const response = await fetch(`${API_BASE_URL}/bookings/`, { method: 'POST', body: formData });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.message || 'Booking failed.');
    alert(`Booking submitted successfully. Reference No: ${payload.data.reference_no}`);
    document.querySelectorAll('input, textarea, select').forEach((el) => {
      if (el.type === 'checkbox' || el.type === 'radio') el.checked = false;
      else if (el.type !== 'button' && el.type !== 'submit') el.value = '';
      clearFieldError(el);
    });
    await loadCustomerPackages();
    await updatePrice();
  } catch (err) {
    const message = err?.message === 'Failed to fetch'
      ? 'Cannot reach the booking server. Make sure Flask is running and try again.'
      : err.message;
    alert(message);
  }
}

async function loadReviews() {
  try {
    const data = await api('/reviews');
    const items = Array.isArray(data?.items) ? data.items : [];
    const grid = document.getElementById('reviewsGrid');
    if (!grid) return;

    grid.innerHTML = items.length ? items.map((review) => {
      const media = Array.isArray(review.media) ? review.media : [];
      const adminReply = review.admin_reply || '';

      return `
        <div class="review-card">
          <div class="review-header">
            <div class="reviewer-avatar">${(review.guest_name || 'G').charAt(0)}</div>
            <div class="reviewer-info">
              <div class="name">${escapeHtml(review.guest_name || 'Guest')}</div>
              <div class="date">${review.created_at ? new Date(review.created_at).toLocaleDateString('en-PH') : '—'}</div>
            </div>
          </div>

          <div class="review-stars">${'★'.repeat(Number(review.rating || 0))}${'☆'.repeat(5 - Number(review.rating || 0))}</div>
          <div class="review-text">"${escapeHtml(review.body || '')}"</div>

          ${
            media.length ? `
              <div class="review-media-gallery">
                ${media.map((item) => {
                  const rawUrl = item.url || item.file_url || item.media_url || '';
                  const url = rawUrl.startsWith('http') ? rawUrl : `${window.location.origin}${rawUrl}`;
                  const type = (item.type || item.media_type || '').toLowerCase();

                  if (type.startsWith('video')) {
                    return `
                      <div class="review-media-item">
                        <video controls preload="metadata">
                          <source src="${url}">
                          Your browser does not support video playback.
                        </video>
                      </div>
                    `;
                  }

                  return `
                    <div class="review-media-item">
                      <img src="${url}" alt="Review media">
                    </div>
                  `;
                }).join('')}
              </div>
            ` : ''
          }

          ${
            adminReply ? `
              <div class="review-admin-reply">
                <div class="reply-label">Admin Reply</div>
                <div class="reply-text">${escapeHtml(adminReply)}</div>
              </div>
            ` : ''
          }
        </div>
      `;
    }).join('') : '<p style="color:white;">No reviews yet.</p>';
  } catch (err) {
    console.warn('Failed to load reviews:', err.message);
  }
}

async function submitReview() {
  const guestName = document.getElementById('reviewName')?.value.trim();
  const body = document.getElementById('reviewText')?.value.trim();
  const rating = document.querySelector('input[name="rating"]:checked')?.value || document.querySelector('input[id^="star"]:checked')?.value;
  const files = document.getElementById('reviewImages')?.files || [];

  if (!guestName || !body || !rating) {
    alert('Please complete the review form.');
    return;
  }

  if (files.length > 6) {
    alert('You can upload up to 6 photos or videos only.');
    return;
  }

  const formData = new FormData();
  formData.append('guest_name', guestName);
  formData.append('body', body);
  formData.append('rating', rating);
  [...files].forEach((file) => formData.append('media', file));

  try {
    const response = await fetch(`${API_BASE_URL}/reviews/`, { method: 'POST', body: formData });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.message || 'Failed to submit review.');
    document.getElementById('reviewModal')?.classList.remove('open');
    document.getElementById('reviewName').value = '';
    document.getElementById('reviewText').value = '';
    const mediaInput = document.getElementById('reviewImages');
    if (mediaInput) mediaInput.value = '';
    document.querySelectorAll('input[name="rating"]').forEach((input) => { input.checked = false; });
    showToast('successToast', 'Thank you for your review!');
    await loadReviews();
  } catch (err) {
    alert(err.message);
  }
}

async function renderCalendar() {
  const datesContainer = document.getElementById('dates');
  const monthYearEl = document.getElementById('month-year');
  if (!datesContainer || !monthYearEl) return;

  const year = currentCalendarDate.getFullYear();
  const monthIndex = currentCalendarDate.getMonth();
  const apiMonth = monthIndex + 1;
  monthYearEl.textContent = currentCalendarDate.toLocaleString('default', { month: 'long', year: 'numeric' });

  datesContainer.innerHTML = '';
  try {
    const data = await api(`/calendar/month?year=${year}&month=${apiMonth}`);
    const firstDay = new Date(year, monthIndex, 1).getDay();
    for (let i = 0; i < firstDay; i += 1) {
      const empty = document.createElement('div');
      empty.className = 'cal-date empty';
      datesContainer.appendChild(empty);
    }

    data.days.forEach((day) => {
      const dateObj = new Date(day.date);
      const cell = document.createElement('div');
      cell.className = 'cal-date';
      cell.textContent = String(dateObj.getDate());
      cell.dataset.dateKey = day.date;
      if (selectedCalendarDate === day.date) cell.classList.add('selected');

      const todayKey = new Date().toISOString().split('T')[0];
      if (day.date < todayKey) cell.classList.add('past');
      else if (day.status === 'available') cell.classList.add('available');
      else if (day.status === 'dayswimming') cell.classList.add('day-booked');
      else if (day.status === 'nightswimming') cell.classList.add('night-booked');
      else if (day.status === 'overnight') cell.classList.add('overnight-booked');
      else cell.classList.add('multi-booked');

      cell.addEventListener('click', async () => {
        selectedCalendarDate = day.date;
        await renderCalendar();
        renderSlots(day.date);
      });
      datesContainer.appendChild(cell);
    });
  } catch (err) {
    datesContainer.innerHTML = `<p>${err.message}</p>`;
  }
}

async function renderSlots(dateKey) {
  const selectedDateLabel = document.getElementById('selectedDateLabel');
  const slotsBody = document.getElementById('slotsBody');
  if (!selectedDateLabel || !slotsBody) return;

  try {
    const data = await api(`/calendar/date?date=${dateKey}`);
    selectedDateLabel.textContent = new Date(dateKey).toLocaleDateString('en-PH', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    const types = [
      ['dayswimming', 'Day Swimming', '6:00 AM – 5:00 PM'],
      ['nightswimming', 'Night Swimming', '6:00 PM – 5:00 AM'],
      ['overnight', 'Overnight', '8:00 AM – 8:00 AM'],
    ];
    slotsBody.innerHTML = types.map(([type, label, time]) => {
      const booked = data.slots.find((slot) => slot.type === type);
      return `
        <div class="slot-row">
          <div class="slot-badge ${booked ? `badge-${type === 'dayswimming' ? 'day' : type === 'nightswimming' ? 'night' : 'overnight'}` : 'badge-available'}"></div>
          <div class="slot-info">
            <div class="slot-type">${label}</div>
            <div class="slot-time">${time}</div>
          </div>
          <div class="slot-status ${booked ? 'status-booked' : 'status-available'}">${booked ? 'Booked' : 'Open'}</div>
        </div>`;
    }).join('');
  } catch (err) {
    slotsBody.innerHTML = `<p>${err.message}</p>`;
  }
}

function bindEvents() {
  document.getElementById('openReviewModal')?.addEventListener('click', () => document.getElementById('reviewModal')?.classList.add('open'));
  document.getElementById('closeModal')?.addEventListener('click', () => document.getElementById('reviewModal')?.classList.remove('open'));
  document.getElementById('toggleReviews')?.addEventListener('click', async () => {
    const panel = document.getElementById('reviewsPanel');
    const open = panel?.classList.toggle('visible');
    if (open) await loadReviews();
  });
  document.getElementById('submitReview')?.addEventListener('click', submitReview);
  document.getElementById('confirmBtn')?.addEventListener('click', submitBooking);
  document.getElementById('prev')?.addEventListener('click', async () => { currentCalendarDate.setMonth(currentCalendarDate.getMonth() - 1); await renderCalendar(); });
  document.getElementById('next')?.addEventListener('click', async () => { currentCalendarDate.setMonth(currentCalendarDate.getMonth() + 1); await renderCalendar(); });

  ['checkIn', 'adults', 'children', 'accomSelect', 'timeSelect'].forEach((id) => {
    document.getElementById(id)?.addEventListener('change', updatePrice);
    document.getElementById(id)?.addEventListener('input', updatePrice);
  });

  document.querySelectorAll('input[name="bayadmethod"]').forEach((radio) => {
    radio.addEventListener('change', () => {
      ['cardFields', 'gcashFields', 'cashFields'].forEach((id) => document.getElementById(id)?.classList.remove('visible'));
      if (radio.value === 'paymaya') document.getElementById('cardFields')?.classList.add('visible');
      if (radio.value === 'gcash') document.getElementById('gcashFields')?.classList.add('visible');
      if (radio.value === 'cash') document.getElementById('cashFields')?.classList.add('visible');
    });
  });
}

(async function init() {
  const today = new Date().toISOString().split('T')[0];
  const checkIn = document.getElementById('checkIn');
  if (checkIn) checkIn.min = today;

  bindEvents();
  await loadPackages();
  await updatePrice();
  await loadReviews();
  await renderCalendar();
  gotoPage('page-main');
})();
