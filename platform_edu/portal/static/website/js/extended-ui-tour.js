/**
 * Tour
 */

'use strict';

(function () {
  const startBtn = document.querySelector('#shepherd-example');

  function setupTour(tour) {
    const backBtnClass = 'btn btn-sm btn-outline-secondary md-btn-flat waves-effect',
      nextBtnClass = 'btn btn-sm btn-primary btn-next waves-effect waves-light';
    
    // First step: Highlight the Questionbank
    tour.addStep({
      title: 'Questionbank',
      text: 'Welcome to Edunade Academy! Let\'s start with the Questionbank - your main study resource with thousands of practice questions organized by subject and topic.',
      attachTo: { element: '[data-i18n="Questionbank"]', on: 'right' },
      buttons: [
        {
          action: tour.cancel,
          classes: backBtnClass,
          text: 'Skip Tour'
        },
        {
          text: 'Next',
          classes: nextBtnClass,
          action: tour.next
        }
      ]
    });

    // Second step: Navbar
    tour.addStep({
      title: 'Navigation Bar',
      text: 'This is your main navigation bar where you can access different sections of the platform.',
      attachTo: { element: '.navbar', on: 'bottom' },
      buttons: [
        {
          action: tour.cancel,
          classes: backBtnClass,
          text: 'Skip Tour'
        },
        {
          text: 'Back',
          classes: backBtnClass,
          action: tour.back
        },
        {
          text: 'Next',
          classes: nextBtnClass,
          action: tour.next
        }
      ]
    });

    // Third step: Past Papers by Year
    tour.addStep({
      title: 'Past Papers by Year',
      text: 'Access past examination papers organized by year to practice with real exam questions.',
      attachTo: { element: '[data-i18n="Past Papers by Year"]', on: 'right' },
      buttons: [
        {
          text: 'Skip Tour',
          classes: backBtnClass,
          action: tour.cancel
        },
        {
          text: 'Back',
          classes: backBtnClass,
          action: tour.back
        },
        {
          text: 'Next',
          classes: nextBtnClass,
          action: tour.next
        }
      ]
    });

    // Fourth step: Past Papers by Topic
    tour.addStep({
      title: 'Past Papers by Topic',
      text: 'Find past paper questions organized by specific topics to focus your practice.',
      attachTo: { element: '[data-i18n="Past Papers by Topic"]', on: 'right' },
      buttons: [
        {
          text: 'Skip Tour',
          classes: backBtnClass,
          action: tour.cancel
        },
        {
          text: 'Back',
          classes: backBtnClass,
          action: tour.back
        },
        {
          text: 'Next',
          classes: nextBtnClass,
          action: tour.next
        }
      ]
    });



    tour.addStep({
      title: 'University Database',
      text: 'Find the perfct university from more than 15,000 programmes!',
      attachTo: { element: '[data-i18n="University Database"]', on: 'right' },
      buttons: [
        {
          text: 'Skip Tour',
          classes: backBtnClass,
          action: tour.cancel
        },
        {
          text: 'Back',
          classes: backBtnClass,
          action: tour.back
        },
        {
          text: 'Next',
          classes: nextBtnClass,
          action: tour.next
        }
      ]
    });


    tour.addStep({
      title: 'Suitability Survey',
      text: 'Find the perfect studdy programme!',
      attachTo: { element: '[data-i18n="Suitability Survey"]', on: 'right' },
      buttons: [
        {
          text: 'Skip Tour',
          classes: backBtnClass,
          action: tour.cancel
        },
        {
          text: 'Back',
          classes: backBtnClass,
          action: tour.back
        },
        {
          text: 'Next',
          classes: nextBtnClass,
          action: tour.next
        }
      ]
    });

    // Fifth step: Settings
    tour.addStep({
      title: 'Settings',
      text: 'Manage your account, security, and subscription settings here.',
      attachTo: { element: '[data-i18n="Settings"]', on: 'right' },
      buttons: [
        {
          text: 'Skip Tour',
          classes: backBtnClass,
          action: tour.cancel
        },
        {
          text: 'Back',
          classes: backBtnClass,
          action: tour.back
        },
        {
          text: 'Finish Tour',
          classes: nextBtnClass,
          action: tour.cancel
        }
      ]
    });

    return tour;
  }

  if (startBtn) {
    // On start tour button click
    startBtn.onclick = function () {
      const tourVar = new Shepherd.Tour({
        defaultStepOptions: {
          scrollTo: true,
          cancelIcon: {
            enabled: true
          }
        },
        useModalOverlay: true
      });

      setupTour(tourVar).start();
    };
  }

  // ! Documentation Tour only
  const startBtnDocs = document.querySelector('#shepherd-docs-example');

  function setupTourDocs(tour) {
    const backBtnClass = 'btn btn-sm btn-label-secondary md-btn-flat waves-effect',
      nextBtnClass = 'btn btn-sm btn-primary btn-next waves-effect waves-light';
    tour.addStep({
      title: 'Navbar',
      text: 'This is your navbar',
      attachTo: { element: '.navbar', on: 'bottom' },
      buttons: [
        {
          action: tour.cancel,
          classes: backBtnClass,
          text: 'Skip'
        },
        {
          text: 'Next',
          classes: nextBtnClass,
          action: tour.next
        }
      ]
    });
    tour.addStep({
      title: 'Footer',
      text: 'This is the Footer',
      attachTo: { element: '.footer', on: 'top' },
      buttons: [
        {
          text: 'Skip',
          classes: backBtnClass,
          action: tour.cancel
        },
        {
          text: 'Back',
          classes: backBtnClass,
          action: tour.back
        },
        {
          text: 'Next',
          classes: nextBtnClass,
          action: tour.next
        }
      ]
    });
    tour.addStep({
      title: 'Social Link',
      text: 'Click here share on social media',
      attachTo: { element: '.footer-link', on: 'top' },
      buttons: [
        {
          text: 'Back',
          classes: backBtnClass,
          action: tour.back
        },
        {
          text: 'Finish',
          classes: nextBtnClass,
          action: tour.cancel
        }
      ]
    });

    return tour;
  }

  if (startBtnDocs) {
    // On start tour button click
    startBtnDocs.onclick = function () {
      const tourDocsVar = new Shepherd.Tour({
        defaultStepOptions: {
          scrollTo: false,
          cancelIcon: {
            enabled: true
          }
        },
        useModalOverlay: true
      });

      setupTourDocs(tourDocsVar).start();
    };
  }
})();
