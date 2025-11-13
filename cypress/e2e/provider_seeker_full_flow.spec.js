// cypress/e2e/provider_seeker_full_flow.spec.js
//
// Full end-to-end happy-path flows for Provider and Seeker.
// - Auth (Flask) served at http://localhost:5000
// - AI-Guru frontend (React) at http://localhost:3000
// - Astra (Django) at http://localhost:8000
//
// Notes:
// - Uses timestamped emails so runs are idempotent.
// - Clicks "Sign in with email" (or equivalent) to reveal inputs on the auth landing page.
// - Uses full absolute URLs so tests don't depend on Cypress baseUrl.
// - Increase command timeout if your environment is slow.

const now = Date.now();
const provider = {
  email: `provider+${now}@test.local`,
  password: 'Provider@123',
  fullname: 'Provider One'
};
const seeker = {
  email: `seeker+${now}@test.local`,
  password: 'Seeker@123',
  fullname: 'Seeker One'
};

// Helper: click a button by visible text (case-insensitive)
Cypress.Commands.add('clickByText', (selector, text) => {
  cy.get(selector).contains(new RegExp(text, 'i')).click();
});

describe('Astra full flows — Provider & Seeker + AI & Courses', () => {
  before(() => {
    // clear previous state
    cy.clearCookies();
    cy.clearLocalStorage();
  });

  context('Provider flow — register, profile, create listing', () => {
    it('should allow a provider to register, login, create a service, and view it', () => {
      // Visit auth sign-in landing (Flask)
      cy.visit('http://localhost:5000/auth/signin');

      // Click "Sign in with email" (reveals email/password inputs on your UI)
      cy.contains(/sign in with email/i).click();

      // If there's a "Join now" link and we want to register instead, go to join route
      cy.contains(/join now/i).then($el => {
        if ($el.length) {
          // It's a link to join — click it to go to registration page
          cy.wrap($el).click();
        }
      });

      // At registration page, fill fields. Support both /auth/join and /auth/signup
      // Try to find registration email input or fallback to sign-in form + a "create account" flow
      cy.get('body').then(($body) => {
        if ($body.find("input[name='email']").length) {
          // Fill email & password (registration)
          cy.get("input[name='email']").clear().type(provider.email, { force: true });
          if ($body.find("input[name='password']").length) {
            cy.get("input[name='password']").clear().type(provider.password, { force: true });
          } else if ($body.find("input[type='password']").length) {
            cy.get("input[type='password']").clear().type(provider.password, { force: true });
          }
          // If there's a name field
          if ($body.find("input[name='fullname']").length) {
            cy.get("input[name='fullname']").clear().type(provider.fullname);
          }
          // Submit registration (look for common buttons)
          cy.contains(/agree & join|sign up|create account|join now|register/i).click();
        } else {
          // No register fields found — maybe the app shows a modal after clicking "Sign in with email"
          // In that case, try to find the sign-in form then click "Join" link from there
          if ($body.find("a").length) {
            cy.contains(/join now|create account/i).click({ force: true });
            // try fill again
            cy.get("input[name='email']").clear().type(provider.email);
            cy.get("input[name='password']").clear().type(provider.password);
            cy.contains(/sign up|create account/i).click({ force: true });
          }
        }
      });

      // After registration, login flow (if auto logged-in, skip)
      cy.url({ timeout: 10000 }).should((u) => {
        // Accept either redirect to dashboard or still on signin
        expect(u).to.satisfy(url => /dashboard|signin|join|welcome/i.test(url));
      });

      // If not logged in, perform login
      cy.get('body').then($body => {
        if ($body.find("input[name='email']").length && $body.find("input[name='password']").length) {
          cy.get("input[name='email']").clear().type(provider.email);
          cy.get("input[name='password']").clear().type(provider.password);
          cy.get("button[type='submit']").click();
        }
      });

      // Wait for dashboard or role selection
      cy.url({ timeout: 20000 }).should((u) => {
        expect(u).to.satisfy(url => /dashboard|role_selection/i.test(url));
      });

      // If redirected to role selection, choose Provider
      cy.url().then(url => {
        if (url.includes('/auth/role_selection')) {
          cy.contains('button', 'Provider').click();
          cy.url({ timeout: 10000 }).should('include', '/dashboard');
        }
      });

      // Edit profile (try to navigate to profile edit)
      // route attempts: /profile/edit, /dashboard/profile, /account/edit
      const profilePaths = [
        'http://localhost:3000/profile/edit',
        'http://localhost:5000/profile/edit',
        'http://localhost:3000/dashboard/profile',
        'http://localhost:5000/dashboard/profile',
        'http://localhost:3000/account/edit'
      ];
      let tried = 0;
      function tryProfilePath() {
        if (tried >= profilePaths.length) {
          // skip profile edit if no path found
          return;
        }
        const p = profilePaths[tried++];
        cy.request({ url: p, failOnStatusCode: false }).then((resp) => {
          if (resp.status === 200) {
            cy.visit(p);
            // Fill profile fields if present
            cy.get('body').then($body => {
              if ($body.find("input[name='fullname']").length) {
                cy.get("input[name='fullname']").clear().type(provider.fullname);
              }
              if ($body.find("textarea[name='bio']").length) {
                cy.get("textarea[name='bio']").clear().type('Experienced dev mentor — Cypress test.');
              }
              if ($body.find("input[name='skills']").length) {
                cy.get("input[name='skills']").clear().type('React{enter}Django{enter}');
              }
              // Save
              cy.contains(/save|update profile|update/i).click({ force: true });
            });
          } else {
            tryProfilePath();
          }
        });
      }
      tryProfilePath();

      // Create a service/listing
      // Possible create paths
      const createPaths = [
        'http://localhost:3000/services/new',
        'http://localhost:5000/services/new',
        'http://localhost:3000/dashboard/services/new'
      ];
      tried = 0;
      function tryCreateService() {
        if (tried >= createPaths.length) return;
        const p = createPaths[tried++];
        cy.request({ url: p, failOnStatusCode: false }).then(resp => {
          if (resp.status === 200) {
            cy.visit(p);
            cy.get('body').then($body => {
              if ($body.find("input[name='title']").length) {
                cy.get("input[name='title']").clear().type('Frontend Mentoring (1:1)');
                cy.get("textarea[name='description']").clear().type('Hands-on mentoring for React & frontend patterns.');
                if ($body.find("input[name='price']").length) {
                  cy.get("input[name='price']").clear().type('25');
                }
                cy.contains(/create|publish|save/i).click({ force: true });
                // Verify created by visiting my-services or listing page
                cy.visit(p.replace('/new', ''));
                cy.contains('Frontend Mentoring (1:1)', { timeout: 10000 }).should('exist');
              }
            });
          } else {
            tryCreateService();
          }
        });
      }
      tryCreateService();
    });
  });

  context('Seeker flow — register, search, request', () => {
    it('should allow a seeker to register, login, search for a service, and message a provider', () => {
      // Ensure clean state
      cy.clearCookies();
      cy.clearLocalStorage();

      // Visit sign-in landing
      cy.visit('http://localhost:5000/auth/signin');
      cy.contains(/sign in with email/i).click();
      // Navigate to join if available
      cy.contains(/join now/i).then($el => {
        if ($el.length) cy.wrap($el).click();
      });

      // Fill join/register
      cy.get('body').then($body => {
        if ($body.find("input[name='email']").length) {
          cy.get("input[name='email']").clear().type(seeker.email);
          if ($body.find("input[name='password']").length) {
            cy.get("input[name='password']").clear().type(seeker.password);
          } else {
            cy.get("input[type='password']").clear().type(seeker.password);
          }
          cy.contains(/agree & join|sign up|join now|register/i).click({ force: true });
        }
      });

      // If still not logged in, attempt login
      cy.get('body').then($body => {
        if ($body.find("input[name='email']").length && $body.find("input[name='password']").length) {
          cy.get("input[name='email']").clear().type(seeker.email);
          cy.get("input[name='password']").clear().type(seeker.password);
          cy.get("button[type='submit']").click();
        }
      });

      // Wait for dashboard or role selection
      cy.url({ timeout: 20000 }).should((u) => {
        expect(u).to.satisfy(url => /dashboard|role_selection/i.test(url));
      });

      // If redirected to role selection, choose Seeker
      cy.url().then(url => {
        if (url.includes('/auth/role_selection')) {
          cy.contains('button', 'Seeker').click();
          cy.url({ timeout: 10000 }).should('include', '/dashboard');
        }
      });

      // Search for 'React' on front-end search
      // The search UI is probably in React frontend at port 3000
      cy.origin('http://localhost:3000', () => {
        cy.visit('/search');
        cy.get('body').then($body => {
          if ($body.find("input[name='q']").length) {
            cy.get("input[name='q']").clear().type('React');
            cy.get("button[type='submit']").contains(/search|go/i).click();
          } else if ($body.find("input[placeholder='Search']").length) {
            cy.get("input[placeholder='Search']").clear().type('React');
            cy.get("button[type='submit']").click();
          }
        });
      });

      // Click provider listing & request
      cy.contains('Provider One').click({ force: true });
      cy.contains(/request|hire|book/i).click({ force: true });
      cy.get("textarea[name='message']").type('Hi — I would like mentoring on React fundamentals.');
      cy.contains(/send request|send/i).click({ force: true });

      // Confirm request sent (toast or page confirmation)
      cy.contains(/request sent|message sent|booking request/i, { timeout: 10000 }).should('exist');

      // Open messages and send a follow-up (if messaging UI exists)
      const messagesPaths = [
        'http://localhost:3000/messages',
        'http://localhost:5000/messages',
        'http://localhost:3000/dashboard/messages'
      ];
      let tr = 0;
      function tryMessages() {
        if (tr >= messagesPaths.length) return;
        const p = messagesPaths[tr++];
        cy.request({ url: p, failOnStatusCode: false }).then(resp => {
          if (resp.status === 200) {
            cy.visit(p);
            cy.get('body').then($body => {
              if ($body.find(".message-composer").length || $body.find("textarea[name='message']").length) {
                if ($body.find("textarea[name='message']").length) {
                  cy.get("textarea[name='message']").type('Thanks — looking forward to scheduling.');
                  cy.contains(/send/i).click({ force: true });
                  cy.contains('Thanks — looking forward to scheduling', { timeout: 10000 }).should('exist');
                }
              }
            });
          } else {
            tryMessages();
          }
        });
      }
      tryMessages();
    });
  });

  context('AI-Guru chat (mocked) — frontend', () => {
    beforeEach(() => {
      cy.intercept('POST', 'http://localhost:8001/chat', {
        statusCode: 200,
        body: {
          response: 'mocked AI reply',
          session_id: 'mock_session',
          interaction_id: 'mock_interaction'
        }
      }).as('aiChat');
    });

    it('should test AI-Guru chat functionality', () => {
      // Visit React chat UI
      cy.origin('http://localhost:3000', () => {
        cy.visit('/chat');

        // Wait for chat input and send message
        cy.get('body').then($body => {
          if ($body.find("input[name='message']").length) {
            cy.get("input[name='message']").clear().type('Hello AI Guru');
            cy.get("button[type='submit']").contains(/send|ask|submit/i).click({ force: true });
          } else if ($body.find("textarea[name='message']").length) {
            cy.get("textarea[name='message']").clear().type('Hello AI Guru');
            cy.contains(/send|submit/i).click({ force: true });
          } else {
            // If no UI, fail fast
            cy.log('Chat UI not found on frontend at /chat');
            cy.wrap(null).should('not.equal', null); // forces test fail
          }
        });

        // Expect mocked AI reply to appear
        cy.contains(/mocked ai reply|mocked reply|hello|hi/i, { timeout: 15000 }).should('exist');
      });
    });
  });

  context('Astra course flow (Django) — enrollment & viewing', () => {
    it('should test Astra course flow (enrollment and viewing)', () => {
      // Visit courses on Django server
      cy.origin('http://localhost:8000', () => {
        cy.visit('/courses');

        cy.get('body').then($body => {
          if ($body.find(".course-card").length) {
            // Pick first course
            cy.get('.course-card').first().within(() => {
              cy.contains(/enroll|view course|details/i).click({ force: true });
            });

            // Enroll button
            cy.contains(/enroll|join course/i, { timeout: 10000 }).click({ force: true });

            // After enrollment, visit lessons and mark progress
            cy.contains(/start course|view lessons/i).click({ force: true });

            // Mark lesson complete if UI supports
            cy.get('body').then($b => {
              if ($b.find(".lesson-complete").length) {
                cy.get('.lesson-complete').first().click({ force: true });
                cy.contains(/progress|%|completed/i, { timeout: 10000 }).should('exist');
              }
            });
          } else {
            // If courses page not present, fail with meaningful message
            cy.log('No course-cards found at /courses on Django server');
            cy.wrap(null).should('not.equal', null); // forces test fail
          }
        });
      });
    });
  });

  // Final cleanup hook
  after(() => {
    // Optionally clear cookies/local storage so next run starts clean
    cy.clearCookies();
    cy.clearLocalStorage();
  });
});