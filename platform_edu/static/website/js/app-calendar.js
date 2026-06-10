/**
 * App Calendar
 */

/**
 * ! If both start and end dates are same Full calendar will nullify the end date value.
 * ! Full calendar will end the event on a day before at 12:00:00AM thus, event won't extend to the end date.
 * ! We are getting events from a separate file named app-calendar-events.js. You can add or remove events from there.
 *
 **/

'use strict';

document.addEventListener('DOMContentLoaded', function () {
  // Setup CSRF token for AJAX requests (Django requirement)
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  
  // Add CSRF token to AJAX requests
  const csrftoken = getCookie('csrftoken');
  
  // Set up AJAX headers
  $.ajaxSetup({
    beforeSend: function(xhr, settings) {
      if (!this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
      }
    }
  });

  const direction = isRtl ? 'rtl' : 'ltr';
  (function () {
    // DOM Elements
    const calendarEl = document.getElementById('calendar');
    const appCalendarSidebar = document.querySelector('.app-calendar-sidebar');
    const addEventSidebar = document.getElementById('addEventSidebar');
    const appOverlay = document.querySelector('.app-overlay');
    const offcanvasTitle = document.querySelector('.offcanvas-title');
    const btnToggleSidebar = document.querySelector('.btn-toggle-sidebar');
    const btnSubmit = document.getElementById('addEventBtn');
    const btnDeleteEvent = document.querySelector('.btn-delete-event');
    const btnCancel = document.querySelector('.btn-cancel');
    const eventTitle = document.getElementById('eventTitle');
    const eventStartDate = document.getElementById('eventStartDate');
    const eventEndDate = document.getElementById('eventEndDate');
    const eventUrl = document.getElementById('eventURL');
    const eventLocation = document.getElementById('eventLocation');
    const eventDescription = document.getElementById('eventDescription');
    const allDaySwitch = document.querySelector('.allDay-switch');
    const selectAll = document.querySelector('.select-all');
    const filterInputs = Array.from(document.querySelectorAll('.input-filter'));
    const inlineCalendar = document.querySelector('.inline-calendar');

    // Calendar settings
    const calendarColors = {
      Business: 'primary',
      Holiday: 'success',
      Personal: 'danger',
      Family: 'warning',
      ETC: 'info'
    };

    // External jQuery Elements
    const eventLabel = $('#eventLabel'); // ! Using jQuery vars due to select2 jQuery dependency
    const eventGuests = $('#eventGuests'); // ! Using jQuery vars due to select2 jQuery dependency

    // Event Data
    let currentEvents = window.events || []; // Use window.events instead of events and provide fallback
    console.log("Initial events loaded:", currentEvents);
    let isFormValid = false;
    let eventToUpdate = null;
    let inlineCalInstance = null;

    // Offcanvas Instance
    const bsAddEventSidebar = new bootstrap.Offcanvas(addEventSidebar);

    //! TODO: Update Event label and guest code to JS once select removes jQuery dependency
    // Initialize Select2 with custom templates
    if (eventLabel.length) {
      function renderBadges(option) {
        if (!option.id) {
          return option.text;
        }
        var $badge =
          "<span class='badge badge-dot bg-" + $(option.element).data('label') + " me-2'> " + '</span>' + option.text;

        return $badge;
      }
      select2Focus(eventLabel);
      eventLabel.select2({
        placeholder: 'Select value',
        dropdownParent: eventLabel.parent(),
        templateResult: renderBadges,
        templateSelection: renderBadges,
        minimumResultsForSearch: -1,
        escapeMarkup: function (es) {
          return es;
        }
      });
    }

    // Render guest avatars
    if (eventGuests.length) {
      function renderGuestAvatar(option) {
        if (!option.id) return option.text;
        return `
<div class='d-flex flex-wrap align-items-center'>
<div class='avatar avatar-xs me-2'>
<img src='${assetsPath}img/avatars/${$(option.element).data('avatar')}'
alt='avatar' class='rounded-circle' />
</div>
      ${option.text}
</div>`;
      }
      select2Focus(eventGuests);
      eventGuests.select2({
        placeholder: 'Select value',
        dropdownParent: eventGuests.parent(),
        closeOnSelect: false,
        templateResult: renderGuestAvatar,
        templateSelection: renderGuestAvatar,
        escapeMarkup: function (es) {
          return es;
        }
      });
    }

    // Event start (flatpicker)
    if (eventStartDate) {
      var start = eventStartDate.flatpickr({
        monthSelectorType: 'static',
        static: true,
        enableTime: true,
        altFormat: 'Y-m-dTH:i:S',
        onReady: function (selectedDates, dateStr, instance) {
          if (instance.isMobile) {
            instance.mobileInput.setAttribute('step', null);
          }
        }
      });
    }

    // Event end (flatpicker)
    if (eventEndDate) {
      var end = eventEndDate.flatpickr({
        monthSelectorType: 'static',
        static: true,
        enableTime: true,
        altFormat: 'Y-m-dTH:i:S',
        onReady: function (selectedDates, dateStr, instance) {
          if (instance.isMobile) {
            instance.mobileInput.setAttribute('step', null);
          }
        }
      });
    }

    // Inline sidebar calendar (flatpicker)
    if (inlineCalendar) {
      inlineCalInstance = inlineCalendar.flatpickr({
        monthSelectorType: 'static',
        static: true,
        inline: true
      });
    }

    // Event click function
    function eventClick(info) {
      eventToUpdate = info.event;
      if (eventToUpdate.url) {
        info.jsEvent.preventDefault();
        window.open(eventToUpdate.url, '_blank');
      }
      bsAddEventSidebar.show();
      // For update event set offcanvas title text: Update Event
      if (offcanvasTitle) {
        offcanvasTitle.innerHTML = 'Update Event';
      }
      btnSubmit.innerHTML = 'Update';
      btnSubmit.classList.add('btn-update-event');
      btnSubmit.classList.remove('btn-add-event');
      btnDeleteEvent.classList.remove('d-none');

      eventTitle.value = eventToUpdate.title;
      start.setDate(eventToUpdate.start, true, 'Y-m-d');
      eventToUpdate.allDay === true ? (allDaySwitch.checked = true) : (allDaySwitch.checked = false);
      eventToUpdate.end !== null
        ? end.setDate(eventToUpdate.end, true, 'Y-m-d')
        : end.setDate(eventToUpdate.start, true, 'Y-m-d');
      eventLabel.val(eventToUpdate.extendedProps.calendar).trigger('change');
      eventToUpdate.extendedProps.location !== undefined
        ? (eventLocation.value = eventToUpdate.extendedProps.location)
        : null;
      eventToUpdate.extendedProps.guests !== undefined
        ? eventGuests.val(eventToUpdate.extendedProps.guests).trigger('change')
        : null;
      eventToUpdate.extendedProps.description !== undefined
        ? (eventDescription.value = eventToUpdate.extendedProps.description)
        : null;
    }

    // Modify sidebar toggler
    function modifyToggler() {
      const fcSidebarToggleButton = document.querySelector('.fc-sidebarToggle-button');
      const fcPrevButton = document.querySelector('.fc-prev-button');
      const fcNextButton = document.querySelector('.fc-next-button');
      const fcHeaderToolbar = document.querySelector('.fc-header-toolbar');
      fcPrevButton.classList.add('btn', 'btn-sm', 'btn-icon', 'btn-outline-secondary', 'me-2');
      fcNextButton.classList.add('btn', 'btn-sm', 'btn-icon', 'btn-outline-secondary', 'me-4');
      fcHeaderToolbar.classList.add('row-gap-4', 'gap-2');
      fcSidebarToggleButton.classList.remove('fc-button-primary');
      fcSidebarToggleButton.classList.add('d-lg-none', 'd-inline-block', 'ps-0');
      while (fcSidebarToggleButton.firstChild) {
        fcSidebarToggleButton.firstChild.remove();
      }
      fcSidebarToggleButton.setAttribute('data-bs-toggle', 'sidebar');
      fcSidebarToggleButton.setAttribute('data-overlay', '');
      fcSidebarToggleButton.setAttribute('data-target', '#app-calendar-sidebar');
      fcSidebarToggleButton.insertAdjacentHTML(
        'beforeend',
        '<i class="icon-base ri ri-menu-line icon-24px text-body"></i>'
      );
    }

    // Filter events by calender
    function selectedCalendars() {
      let selected = [];
      const filterInputChecked = document.querySelectorAll('.input-filter:checked');
      
      console.log("Checked filters found:", filterInputChecked.length);
      
      filterInputChecked.forEach(item => {
        const value = item.getAttribute('data-value');
        console.log("Adding filter value to selection:", value);
        selected.push(value);
      });

      console.log("Final selected filters:", selected);
      return selected;
    }

    // --------------------------------------------------------------------------------------------------
    // AXIOS: fetchEvents
    // * This will be called by fullCalendar to fetch events. Also this can be used to refetch events.
    // --------------------------------------------------------------------------------------------------
    function fetchEvents(info, successCallback) {
      let calendars = selectedCalendars();
      console.log("Selected calendars for filtering:", calendars);
      
      // We are reading event object from app-calendar-events.js file directly by including that file above app-calendar file.
      // You should make an API call, look into above commented API call for reference
      let selectedEvents = currentEvents.filter(function (event) {
        // Direct comparison since we've matched the case in the HTML
        const isIncluded = calendars.includes(event.extendedProps.calendar);
        console.log(`Event ${event.id} (${event.title}) with calendar ${event.extendedProps.calendar} ${isIncluded ? 'matches' : 'does not match'} filters`);
        return isIncluded;
      });
      console.log("Filtered events:", selectedEvents);
      successCallback(selectedEvents);
    }

    // Init FullCalendar
    // ------------------------------------------------
    let calendar = new Calendar(calendarEl, {
      initialView: 'dayGridMonth',
      events: fetchEvents,
      plugins: [dayGridPlugin, interactionPlugin, listPlugin, timegridPlugin],
      editable: true,
      dragScroll: true,
      dayMaxEvents: 2,
      eventResizableFromStart: true,
      customButtons: {
        sidebarToggle: {
          text: 'Sidebar'
        }
      },
      headerToolbar: {
        start: 'sidebarToggle, prev,next, title',
        end: 'dayGridMonth,timeGridWeek,timeGridDay,listMonth'
      },
      direction: direction,
      initialDate: new Date(),
      navLinks: true, // can click day/week names to navigate views
      eventClassNames: function ({ event: calendarEvent }) {
        const colorName = calendarColors[calendarEvent._def.extendedProps.calendar];
        // Background Color
        return ['bg-label-' + colorName];
      },
      dateClick: function (info) {
        let date = moment(info.date).format('YYYY-MM-DD');
        resetValues();
        bsAddEventSidebar.show();

        // For new event set offcanvas title text: Add Event
        if (offcanvasTitle) {
          offcanvasTitle.innerHTML = 'Add Event';
        }
        btnSubmit.innerHTML = 'Add';
        btnSubmit.classList.remove('btn-update-event');
        btnSubmit.classList.add('btn-add-event');
        btnDeleteEvent.classList.add('d-none');
        eventStartDate.value = date;
        eventEndDate.value = date;
      },
      eventClick: function (info) {
        eventClick(info);
      },
      datesSet: function () {
        modifyToggler();
      },
      viewDidMount: function () {
        modifyToggler();
      }
    });

    // Render calendar
    calendar.render();
    // Modify sidebar toggler
    modifyToggler();

    const eventForm = document.getElementById('eventForm');
    const fv = FormValidation.formValidation(eventForm, {
      fields: {
        eventTitle: {
          validators: {
            notEmpty: {
              message: 'Please enter event title '
            }
          }
        },
        eventStartDate: {
          validators: {
            notEmpty: {
              message: 'Please enter start date '
            }
          }
        },
        eventEndDate: {
          validators: {
            notEmpty: {
              message: 'Please enter end date '
            }
          }
        }
      },
      plugins: {
        trigger: new FormValidation.plugins.Trigger(),
        bootstrap5: new FormValidation.plugins.Bootstrap5({
          // Use this for enabling/changing valid/invalid class
          eleValidClass: '',
          rowSelector: function (field, ele) {
            // field is the field name & ele is the field element
            return '.form-control-validation';
          }
        }),
        submitButton: new FormValidation.plugins.SubmitButton(),
        // Submit the form when all fields are valid
        // defaultSubmit: new FormValidation.plugins.DefaultSubmit(),
        autoFocus: new FormValidation.plugins.AutoFocus()
      }
    })
      .on('core.form.valid', function () {
        // Jump to the next step when all fields in the current step are valid
        isFormValid = true;
      })
      .on('core.form.invalid', function () {
        // if fields are invalid
        isFormValid = false;
      });

    // Sidebar Toggle Btn
    if (btnToggleSidebar) {
      btnToggleSidebar.addEventListener('click', e => {
        btnCancel.classList.remove('d-none');
      });
    }

    // Add Event
    // ------------------------------------------------
    function addEvent(eventData) {
      // Ensure required fields are present
      if (!eventData.title || !eventData.start) {
        console.error("Missing required event data: title or start");
        return;
      }
    
      // Convert start and end to ISO strings if needed
      if (eventData.start instanceof Date) {
        eventData.start = moment(eventData.start).toISOString(true); // true = keep time zone
      }
    
      if (eventData.end instanceof Date) {
        eventData.end = moment(eventData.end).toISOString(true);
      }
    
      // Clone and clean event data
      const eventToAdd = {
        id: eventData.id || String(Date.now()), // fallback id
        title: eventData.title,
        start: eventData.start,
        end: eventData.end || null, // optional
        allDay: !!eventData.allDay, // default to false if undefined
        url: eventData.url || '',
        extendedProps: {
          ...(eventData.extendedProps || {})
        }
      };
    
      // Add to FullCalendar
      const addedEvent = calendar.addEvent(eventToAdd);
    
      if (!addedEvent) {
        console.error("Event failed to add to calendar");
        return;
      }
    
      console.log("Event added to calendar:", addedEvent);
    
      // Optional: update your custom currentEvents array
      if (Array.isArray(currentEvents)) {
        currentEvents.push(eventToAdd);
        console.log("Current events array updated:", currentEvents);
      }
    
      // Reset form fields
      resetValues();
    
      // No need for calendar.refetchEvents(); it’s for remote sources
    }
    

    // Update Event
    // ------------------------------------------------
    function updateEvent(eventData) {
      // Convert dates to proper format if they're Date objects
      if (eventData.start instanceof Date) {
        console.log("Converting start date to string format:", eventData.start);
        eventData.start = moment(eventData.start).format();
      }
      if (eventData.end instanceof Date) {
        console.log("Converting end date to string format:", eventData.end);
        eventData.end = moment(eventData.end).format();
      }
      
      console.log("Updating event with formatted data:", eventData);
      
      // Find and update the event in the array
      const eventIndex = currentEvents.findIndex(event => event.id === parseInt(eventData.id));
      if (eventIndex !== -1) {
        currentEvents[eventIndex] = {...eventData};
        console.log("Updated event in array at index:", eventIndex);
      } else {
        console.warn("Event not found in array:", eventData.id);
      }

      // Update the event in the calendar
      const calendarEvent = calendar.getEventById(eventData.id);
      if (calendarEvent) {
        console.log("Found event in calendar, updating...");
        
        // Update basic properties
        calendarEvent.setProp('title', eventData.title);
        calendarEvent.setStart(eventData.start);
        calendarEvent.setEnd(eventData.end);
        calendarEvent.setAllDay(eventData.allDay);
        if (eventData.url) {
          calendarEvent.setProp('url', eventData.url);
        }
        
        // Update extended props
        for (const [key, value] of Object.entries(eventData.extendedProps)) {
          calendarEvent.setExtendedProp(key, value);
        }
        
        console.log("Event updated in calendar");
      } else {
        console.warn("Event not found in calendar:", eventData.id);
      }

      // Reset form values and event to update
      resetValues();
      eventToUpdate = null;
    }

    // Remove Event
    // ------------------------------------------------

    function removeEvent(eventId) {
      // ? Delete existing event data to current events object and refetch it to display on calender
      // ? You can write below code to AJAX call success response
      currentEvents = currentEvents.filter(function (event) {
        return event.id != eventId;
      });
      calendar.refetchEvents();

      // ? To delete event directly to calender (won't update currentEvents object)
      // removeEventInCalendar(eventId);
    }

    // (Update Event In Calendar (UI Only)
    // ------------------------------------------------
    const updateEventInCalendar = (existingEvent, propsToUpdate, extendedPropsToUpdate) => {
      // --- Set event properties except date related ----- //
      // ? Docs: https://fullcalendar.io/docs/Event-setProp
      // dateRelatedProps => ['start', 'end', 'allDay']
      // Set each property individually
      existingEvent.setProp('title', propsToUpdate.title);
      if (propsToUpdate.url) {
        existingEvent.setProp('url', propsToUpdate.url);
      }

      // --- Set date related props ----- //
      // ? Docs: https://fullcalendar.io/docs/Event-setDates
      existingEvent.setDates(propsToUpdate.start, propsToUpdate.end, {
        allDay: propsToUpdate.allDay
      });

      // --- Set event's extendedProps ----- //
      // ? Docs: https://fullcalendar.io/docs/Event-setExtendedProp
      // Set each extended property individually
      existingEvent.setExtendedProp('calendar', extendedPropsToUpdate.calendar);
      existingEvent.setExtendedProp('guests', extendedPropsToUpdate.guests);
      existingEvent.setExtendedProp('location', extendedPropsToUpdate.location);
      existingEvent.setExtendedProp('description', extendedPropsToUpdate.description);
    };

    // Remove Event In Calendar (UI Only)
    // ------------------------------------------------
    function removeEventInCalendar(eventId) {
      calendar.getEventById(eventId).remove();
    }

    // Form submit
    document.getElementById('eventForm').addEventListener('submit', function (e) {
      e.preventDefault();
      console.log("Form submitted!");
      
      // Validate form fields directly
      let isFormValid = true;
      if (eventTitle.value.trim() === '') {
        eventTitle.classList.add('is-invalid');
        isFormValid = false;
        console.log("Form validation failed: Title is empty");
      } else {
        eventTitle.classList.remove('is-invalid');
        console.log("Title validation passed:", eventTitle.value);
      }

      // Verify date pickers have valid values
      if (!start || !start.selectedDates || start.selectedDates.length === 0) {
        console.log("Start date is missing or invalid!");
        isFormValid = false;
      } else {
        console.log("Start date selected:", start.selectedDates[0]);
      }
      
      if (!end || !end.selectedDates || end.selectedDates.length === 0) {
        console.log("End date is missing or invalid!");
        // Use start date as fallback
        if (start && start.selectedDates && start.selectedDates.length > 0) {
          console.log("Setting end date to start date");
          end.setDate(start.selectedDates[0]);
          console.log("End date now set to:", end.selectedDates[0]);
        } else {
          isFormValid = false;
        }
      } else {
        console.log("End date selected:", end.selectedDates[0]);
      }

      console.log("Form is valid:", isFormValid);
      console.log("Calendar label selected:", eventLabel.val());
      console.log("All day event:", allDaySwitch.checked);
      
      if (isFormValid) {
        try {
          // Create the event data
          let newEvent = {
            id: eventToUpdate ? eventToUpdate.id : Date.now(),
            title: eventTitle.value,
            start: start.selectedDates[0],
            end: end.selectedDates[0],
            allDay: allDaySwitch.checked,
            extendedProps: {
              calendar: eventLabel.val(),
              guests: eventGuests.val() || [],
              location: eventLocation.value,
              description: eventDescription.value
            }
          };

          if (eventUrl.value) {
            newEvent.url = eventUrl.value;
          }

          console.log("Event data created:", newEvent);
          console.log("Calendar type for new event:", newEvent.extendedProps.calendar);

          // Handle event based on whether we're updating or adding
          if (eventToUpdate) {
            console.log("Updating existing event with ID:", eventToUpdate.id);
            updateEvent(newEvent);
          } else {
            console.log("Adding new event");
            addEvent(newEvent);
          }

          // Refresh the calendar to ensure the new event is displayed
          calendar.refetchEvents();
          console.log("Calendar refreshed after event operation");

          // Hide sidebar after successful operation
          bsAddEventSidebar.hide();
          console.log("Event sidebar hidden");
        } catch (error) {
          console.error("Error processing event:", error);
        }
      }
    });

    // Call removeEvent function
    btnDeleteEvent.addEventListener('click', function () {
      if (eventToUpdate) {
        removeEvent(eventToUpdate.id);
        bsAddEventSidebar.hide();
      }
    });

    // Reset event form inputs values
    // ------------------------------------------------
    function resetValues() {
      // Reset form elements
      eventTitle.value = '';
      eventStartDate.value = '';
      eventEndDate.value = '';
      eventUrl.value = '';
      eventLocation.value = '';
      eventDescription.value = '';
      allDaySwitch.checked = false;
      eventLabel.val('Business').trigger('change');
      eventGuests.val([]).trigger('change');
      
      // Reset validation states
      eventTitle.classList.remove('is-invalid');
      
      // Reset update state
      btnSubmit.innerHTML = 'Add';
      btnSubmit.classList.remove('btn-update-event');
      btnSubmit.classList.add('btn-add-event');
      btnDeleteEvent.classList.add('d-none');
      if (offcanvasTitle) {
        offcanvasTitle.innerHTML = 'Add Event';
      }
      eventToUpdate = null;
    }

    // When modal hides reset input values
    addEventSidebar.addEventListener('hidden.bs.offcanvas', function () {
      resetValues();
    });

    // Hide left sidebar if the right sidebar is open
    btnToggleSidebar.addEventListener('click', e => {
      if (offcanvasTitle) {
        offcanvasTitle.innerHTML = 'Add Event';
      }
      btnSubmit.innerHTML = 'Add';
      btnSubmit.classList.remove('btn-update-event');
      btnSubmit.classList.add('btn-add-event');
      btnDeleteEvent.classList.add('d-none');
      appCalendarSidebar.classList.remove('show');
      appOverlay.classList.remove('show');
    });

    // Calender filter functionality
    // ------------------------------------------------
    if (selectAll) {
      selectAll.addEventListener('click', e => {
        console.log("Select all filter clicked, checked:", e.currentTarget.checked);
        if (e.currentTarget.checked) {
          document.querySelectorAll('.input-filter').forEach(c => {
            c.checked = true;
            console.log(`Checked filter: ${c.getAttribute('data-value')}`);
          });
        } else {
          document.querySelectorAll('.input-filter').forEach(c => {
            c.checked = false;
            console.log(`Unchecked filter: ${c.getAttribute('data-value')}`);
          });
        }
        calendar.refetchEvents();
      });
    }

    if (filterInputs) {
      filterInputs.forEach(item => {
        item.addEventListener('click', () => {
          console.log(`Filter clicked: ${item.getAttribute('data-value')}, checked: ${item.checked}`);
          const allChecked = document.querySelectorAll('.input-filter:checked').length === document.querySelectorAll('.input-filter').length;
          selectAll.checked = allChecked;
          console.log("All filters checked:", allChecked);
          calendar.refetchEvents();
        });
      });
    }

    // Jump to date on sidebar(inline) calendar change
    inlineCalInstance.config.onChange.push(function (date) {
      calendar.changeView(calendar.view.type, moment(date[0]).format('YYYY-MM-DD'));
      modifyToggler();
      appCalendarSidebar.classList.remove('show');
      appOverlay.classList.remove('show');
    });
  })();
});
