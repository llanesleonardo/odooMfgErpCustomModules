odoo.define('customer_quote.open_empty_popup_modal',   [  'web.ActionManager',
'@web/ActionManager',
    '@web/AbstractAction',
    '@web/Dialog',
    '@web/core',
], function (require) {
    'use strict';


    const ActionManager = require('web.ActionManager');
    const AbstractAction = require('web.AbstractAction');
    const Dialog = require('web.Dialog');  // Import the dialog component to use for the modal

    // Register the client action
    ActionManager.include({
        _handleAction: function (action) {
            if (action.tag === 'open_empty_popup_modal') {
                // Create and show the dialog (modal)
                const dialog = new Dialog(this, {
                    title: "Empty Modal",  // Modal title
                    size: 'medium',        // Modal size (medium, large, etc.)
                    $content: $('<div><p>This is an empty modal.</p></div>'),  // Content of the modal (can be customized)
                    buttons: [
                        { text: "Close", close: true },  // Close button
                    ],
                });
                dialog.open();
                return Promise.resolve();
            }
            return this._super.apply(this, arguments);  // Default action handling
        },
    });
});
