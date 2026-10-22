/**
 * UrbanAid - Vanilla JS Interactive Handlers
 * Lightweight script for pure HTML/CSS Flask frontend (No React)
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Auto-dismiss flash alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    const closeBtn = alert.querySelector('.alert-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 250);
      });
    }
    setTimeout(() => {
      if (alert && alert.parentElement) {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 250);
      }
    }, 5000);
  });

  // 2. Demo credentials quick autofill for Login page
  window.fillCredentials = function(role) {
    const emailInput = document.getElementById('login-email');
    const passwordInput = document.getElementById('login-password');
    if (!emailInput || !passwordInput) return;

    if (role === 'customer') {
      emailInput.value = 'customer@urbanaid.com';
      passwordInput.value = 'Customer@123';
    } else if (role === 'provider') {
      emailInput.value = 'provider@urbanaid.com';
      passwordInput.value = 'Provider@123';
    } else if (role === 'admin') {
      emailInput.value = 'admin@urbanaid.com';
      passwordInput.value = 'Admin@123';
    }

    // Visual feedback
    emailInput.style.backgroundColor = '#eef2ff';
    passwordInput.style.backgroundColor = '#eef2ff';
    setTimeout(() => {
      emailInput.style.backgroundColor = '';
      passwordInput.style.backgroundColor = '';
    }, 600);
  };

  // 3. Dynamic role toggle in Registration form
  const roleSelect = document.getElementById('reg-role');
  const providerFields = document.getElementById('provider-specific-fields');
  if (roleSelect && providerFields) {
    const toggleFields = () => {
      if (roleSelect.value === 'provider') {
        providerFields.style.display = 'block';
      } else {
        providerFields.style.display = 'none';
      }
    };
    roleSelect.addEventListener('change', toggleFields);
    toggleFields(); // Initial state
  }

  // 4. Review Modal controls
  window.openReviewModal = function(bookingId, providerName, serviceName) {
    const modal = document.getElementById('review-modal');
    const bookingIdInput = document.getElementById('review-booking-id');
    const providerSpan = document.getElementById('modal-provider-name');
    const serviceSpan = document.getElementById('modal-service-name');

    if (modal && bookingIdInput) {
      bookingIdInput.value = bookingId;
      if (providerSpan) providerSpan.textContent = providerName || 'Service Expert';
      if (serviceSpan) serviceSpan.textContent = serviceName || 'Service';
      modal.classList.add('open');
    }
  };

  window.closeReviewModal = function() {
    const modal = document.getElementById('review-modal');
    if (modal) modal.classList.remove('open');
  };

  // Close modal when clicking on overlay background
  const reviewModal = document.getElementById('review-modal');
  if (reviewModal) {
    reviewModal.addEventListener('click', (e) => {
      if (e.target === reviewModal) {
        closeReviewModal();
      }
    });
  }
});
