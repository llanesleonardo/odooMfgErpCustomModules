odoo.define('customer_estimate.qty_at_date_widget', function (require) {
    "use strict";

    // Import required modules
    var AbstractField = require('web.AbstractField');
    var fieldRegistry = require('web.field_registry');

    // Define the custom widget
    var QtyAtDateWidget = AbstractField.extend({
        template: 'QtyAtDateWidget',
        events: {
            'click': '_onClick',
        },

        init: function (parent, name, record, options) {
            this._super.apply(this, arguments);
            this.date = options.date || false;
        },

        _render: function () {
            var self = this;
            if (this.date && this.recordData.product_id) {
                this._rpc({
                    model: 'product.product',
                    method: '_compute_qty_at_date',
                    args: [this.recordData.product_id.res_id, this.date],
                }).then(function (result) {
                    self.$el.text(result.qty_available);
                });
            } else {
                this.$el.text('N/A');
            }
        },

        _onClick: function () {
            // Add custom behavior if needed
        },
    });

    // Register the widget
    fieldRegistry.add('custom_qty_at_date', QtyAtDateWidget);

    // Return the widget for potential reuse
    return QtyAtDateWidget;
});