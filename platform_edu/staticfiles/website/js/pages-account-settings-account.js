/**
 * Account Settings - Account
 */

'use strict';

document.addEventListener('DOMContentLoaded', function (e) {
  (function () {
    const formAccSettings = document.querySelector('#formAccountSettings'),
      deactivateAcc = document.querySelector('#formAccountDeactivation'),
      deactivateButton = deactivateAcc.querySelector('.deactivate-account'),
      TagifyCountrySuggestionEl = document.querySelector('#TagifyCountrySuggestion'),
      TagifyLanguageSuggestionEl = document.querySelector('#TagifyLanguageSuggestion');

    const whitelist = [
      'Australia',
      'Bangladesh',
      'Belarus',
      'Brazil',
      'Canada',
      'China',
      'France',
      'Germany',
      'India',
      'Indonesia',
      'Israel',
      'Italy',
      'Japan',
      'Korea',
      'Mexico',
      'Philippines',
      'Russian Federation',
      'South Africa',
      'Thailand',
      'Turkey',
      'Ukraine',
      'United Arab Emirates',
      'United Kingdom',
      'United States'
    ];
    const langaugelist = ['Portuguese', 'German', 'French', 'English'];
    // List
    let TagifyCountrySuggestion = new Tagify(TagifyCountrySuggestionEl, {
      whitelist: whitelist,
      maxTags: 20,
      dropdown: {
        maxItems: 20,
        classname: '',
        enabled: 0,
        closeOnSelect: false
      }
    });
    let TagifyLanguageSuggestion = new Tagify(TagifyLanguageSuggestionEl, {
      whitelist: langaugelist,
      dropdown: {
        classname: '',
        enabled: 0,
        closeOnSelect: false
      },
      // Add custom transformers to ensure proper display
      transformTag: function(tagData) {
        // If tag is already an object with value property, extract just the value
        if (tagData.value && typeof tagData.value === 'object' && tagData.value.value) {
          tagData.value = tagData.value.value;
        }
        
        // Clean any JSON-like strings
        if (typeof tagData.value === 'string' && tagData.value.includes('{')) {
          try {
            const parsed = JSON.parse(tagData.value);
            if (parsed && parsed.value) {
              tagData.value = parsed.value;
            }
          } catch(e) {
            // If parsing fails, just use the string as is
          }
        }
        
        return tagData;
      },
      // Override the render to ensure clean display
      templates: {
        tag: function(tagData) {
          return `<tag title="${tagData.value}"
                      contenteditable="false"
                      spellcheck="false"
                      tabIndex="-1"
                      class="tagify__tag ${tagData.class ? tagData.class : ""}"
                      ${this.getAttributes(tagData)}>
                    <x title='' class='tagify__tag__removeBtn' role='button' aria-label='remove tag'></x>
                    <div>
                      <span class='tagify__tag-text'>${tagData.value}</span>
                    </div>
                  </tag>`;
        }
      }
    });
    // Form validation for Add new record
    if (formAccSettings) {
      const fv = FormValidation.formValidation(formAccSettings, {
        fields: {
          firstName: {
            validators: {
              notEmpty: {
                message: 'Please enter first name'
              }
            }
          },
          lastName: {
            validators: {
              notEmpty: {
                message: 'Please enter last name'
              }
            }
          }
        },
        plugins: {
          trigger: new FormValidation.plugins.Trigger(),
          bootstrap5: new FormValidation.plugins.Bootstrap5({
            eleValidClass: '',
            rowSelector: '.form-control-validation'
          }),
          submitButton: new FormValidation.plugins.SubmitButton(),
          // Submit the form when all fields are valid
          defaultSubmit: new FormValidation.plugins.DefaultSubmit(),
          autoFocus: new FormValidation.plugins.AutoFocus()
        },
        init: instance => {
          instance.on('plugins.message.placed', function (e) {
            if (e.element.parentElement.classList.contains('input-group')) {
              e.element.parentElement.insertAdjacentElement('afterend', e.messageElement);
            }
          });
        }
      });
    }

    if (deactivateAcc) {
      const fv = FormValidation.formValidation(deactivateAcc, {
        fields: {
          accountActivation: {
            validators: {
              notEmpty: {
                message: 'Please confirm you want to delete account'
              }
            }
          }
        },
        plugins: {
          trigger: new FormValidation.plugins.Trigger(),
          bootstrap5: new FormValidation.plugins.Bootstrap5({
            eleValidClass: ''
          }),
          submitButton: new FormValidation.plugins.SubmitButton(),
          fieldStatus: new FormValidation.plugins.FieldStatus({
            onStatusChanged: function (areFieldsValid) {
              areFieldsValid
                ? // Enable the submit button
                  // so user has a chance to submit the form again
                  deactivateButton.removeAttribute('disabled')
                : // Disable the submit button
                  deactivateButton.setAttribute('disabled', 'disabled');
            }
          }),
          // Submit the form when all fields are valid
          // defaultSubmit: new FormValidation.plugins.DefaultSubmit(),
          autoFocus: new FormValidation.plugins.AutoFocus()
        },
        init: instance => {
          instance.on('plugins.message.placed', function (e) {
            if (e.element.parentElement.classList.contains('input-group')) {
              e.element.parentElement.insertAdjacentElement('afterend', e.messageElement);
            }
          });
        }
      });
    }

    // Deactivate account alert
    const accountActivation = document.querySelector('#accountActivation');

    // Alert With Functional Confirm Button
    if (deactivateButton) {
      deactivateButton.onclick = function () {
        if (accountActivation.checked == true) {
          Swal.fire({
            text: 'Are you sure you would like to deactivate your account?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Yes',
            customClass: {
              confirmButton: 'btn btn-primary me-2 waves-effect waves-light',
              cancelButton: 'btn btn-outline-secondary waves-effect'
            },
            buttonsStyling: false
          }).then(function (result) {
            if (result.value) {
              Swal.fire({
                icon: 'success',
                title: 'Deleted!',
                text: 'Your file has been deleted.',
                customClass: {
                  confirmButton: 'btn btn-success waves-effect'
                }
              });
            } else if (result.dismiss === Swal.DismissReason.cancel) {
              Swal.fire({
                title: 'Cancelled',
                text: 'Deactivation Cancelled!!',
                icon: 'error',
                customClass: {
                  confirmButton: 'btn btn-success waves-effect'
                }
              });
            }
          });
        }
      };
    }

    // CleaveJ-zen validation

    const phoneNumber = document.querySelector('#phoneNumber'),
      zipCode = document.querySelector('#zipCode');
    // Phone Mask
    if (phoneNumber) {
      phoneNumber.addEventListener('input', event => {
        const cleanValue = event.target.value.replace(/\D/g, '');
        phoneNumber.value = formatGeneral(cleanValue, {
          blocks: [3, 3, 4],
          delimiters: [' ', ' ']
        });
      });
      registerCursorTracker({
        input: phoneNumber,
        delimiter: ' '
      });
    }

    // Pincode
    if (zipCode) {
      zipCode.addEventListener('input', event => {
        zipCode.value = formatNumeral(event.target.value, {
          delimiter: '',
          numeral: true
        });
      });
    }

    // Update/reset user image of account page
    let accountUserImage = document.getElementById('uploadedAvatar');
    const fileInput = document.querySelector('.account-file-input'),
      resetFileInput = document.querySelector('.account-image-reset');

    if (accountUserImage) {
      const resetImage = accountUserImage.src;
      fileInput.onchange = () => {
        if (fileInput.files[0]) {
          accountUserImage.src = window.URL.createObjectURL(fileInput.files[0]);
        }
      };
      resetFileInput.onclick = () => {
        fileInput.value = '';
        accountUserImage.src = resetImage;
      };
    }
  })();
});

// Select2 (jquery)
$(function () {
  // Special handling for currency field
  $('#currency').select2('destroy'); // Destroy any existing instance first
  
  // Initialize the currency select with specific settings
  $('#currency').select2({
    dropdownParent: $('#currency').closest('.form-floating'),
    minimumResultsForSearch: Infinity, // Hide search box
    width: '100%',
    // Very explicitly render just the plain text
    templateResult: function(data) {
      // Only return the text content, no HTML or JSON
      return document.createTextNode(data.text || data.id);
    },
    templateSelection: function(data) {
      // Only return the text content, no HTML or JSON
      return document.createTextNode(data.text || data.id);
    }
  });
  
  // Move the label after initialization so it works with Select2
  setTimeout(function() {
    // Get the form-floating container
    var formFloating = $('#currency').closest('.form-floating');
    
    // Get the label
    var label = formFloating.find('label[for="currency"]');
    
    // Make sure the label is visible and correctly positioned
    if (label.length) {
      // Clone to position after Select2 container (to fix z-index issues)
      var newLabel = label.clone();
      formFloating.find('.select2-container').after(newLabel);
      label.hide(); // Hide the original
      
      // Keep the new label in the same style as the floating labels
      newLabel.css({
        'position': 'absolute',
        'top': '0',
        'left': '0.5rem',
        'padding': '0 0.5rem',
        'background-color': '#fff',
        'z-index': '10',
        'transform': 'scale(0.85) translateY(-0.5rem)',
        'transform-origin': '0 0',
        'opacity': '1',
        'border-radius': '0.375rem'
      });
    }
    
    // Clean any JSON in the selection
    $('#currency').next().find('.select2-selection__rendered').each(function() {
      var text = $(this).text();
      if (text.includes('[') || text.includes('{')) {
        // Extract just the currency name/code
        if (text.toLowerCase().includes('usd')) {
          $(this).text('USD');
        } else if (text.toLowerCase().includes('euro')) {
          $(this).text('Euro');
        } else if (text.toLowerCase().includes('pound')) {
          $(this).text('Pound');
        } else if (text.toLowerCase().includes('bitcoin')) {
          $(this).text('Bitcoin');
        } else {
          // Clean any JSON structure
          $(this).text(text.replace(/[\[\]\{\}"']/g, '').replace(/value:/g, ''));
        }
      }
    });
  }, 200);
  
  // Handle the other select2 elements separately
  var otherSelect2 = $('.select2').not('#currency');
  
  // For all other Select2
  if (otherSelect2.length) {
    otherSelect2.each(function () {
      var $this = $(this);
      select2Focus($this);
      $this.select2({
        dropdownParent: $this.parent(),
        templateSelection: function(data) {
          // Ensure we only return the text value, not any JSON
          if (typeof data.text === 'string') {
            return data.text.replace(/\[.*\]/g, '').replace(/\{.*\}/g, '');
          }
          return data.text;
        },
        templateResult: function(data) {
          if (typeof data.text === 'string') {
            return $('<span>').text(data.text.replace(/\[.*\]/g, '').replace(/\{.*\}/g, ''));
          }
          return data.text;
        }
      });
    });
  }
});
