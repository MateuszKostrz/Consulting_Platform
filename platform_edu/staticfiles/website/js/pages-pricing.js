/**
 * Pricing
 */

'use strict';

document.addEventListener('DOMContentLoaded', function (event) {
  (function () {
    const priceDurationToggler = document.querySelector('.price-duration-toggler'),
      priceMonthlyList = [].slice.call(document.querySelectorAll('.price-monthly')),
      priceYearlyList = [].slice.call(document.querySelectorAll('.price-yearly')),
      pricingLinksMonthly = [].slice.call(document.querySelectorAll('.pricing-link.price-monthly')),
      pricingLinksYearly = [].slice.call(document.querySelectorAll('.pricing-link.price-yearly'));

    function togglePrice() {
      if (priceDurationToggler.checked) {
        // If checked - show yearly
        priceYearlyList.map(function (yearEl) {
          yearEl.classList.remove('d-none');
        });
        priceMonthlyList.map(function (monthEl) {
          monthEl.classList.add('d-none');
        });
        pricingLinksYearly.map(function (yearLink) {
          yearLink.classList.remove('d-none');
        });
        pricingLinksMonthly.map(function (monthLink) {
          monthLink.classList.add('d-none');
        });
      } else {
        // If not checked - show monthly
        priceYearlyList.map(function (yearEl) {
          yearEl.classList.add('d-none');
        });
        priceMonthlyList.map(function (monthEl) {
          monthEl.classList.remove('d-none');
        });
        pricingLinksYearly.map(function (yearLink) {
          yearLink.classList.add('d-none');
        });
        pricingLinksMonthly.map(function (monthLink) {
          monthLink.classList.remove('d-none');
        });
      }
    }
    // togglePrice Event Listener
    togglePrice();

    priceDurationToggler.onchange = function () {
      togglePrice();
    };
  })();
});
