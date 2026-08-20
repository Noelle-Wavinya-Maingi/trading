# -*- coding: utf-8 -*-
from odoo import fields, models


class ProcessBridgeTestStep(models.Model):
    """Test-only concrete step model, playing the role a vertical's own
    step model plays for process.step.mixin (e.g. a freight work order).

    Deliberately lives in models/, not tests/: a model defined only inside
    a tests/ file never joins the registry (see
    shared/order_bridge/models/order_bridge_test_host.py for the same
    reasoning), and process.step.mixin/process.template.step.mixin are
    AbstractModels with no concrete model of their own to test against."""
    _name = 'process.bridge.test.step'
    _description = 'Process Bridge Test Step'
    _inherit = ['process.step.mixin']

    host_id = fields.Many2one('process.bridge.test.host', ondelete='cascade')


class ProcessBridgeTestHost(models.Model):
    """Test-only stand-in for an anchor model (trading.trade, a freight file)."""
    _name = 'process.bridge.test.host'
    _description = 'Process Bridge Test Host'
    _inherit = ['process.bridge.mixin']

    name = fields.Char(default='Test Host')
    step_ids = fields.One2many('process.bridge.test.step', 'host_id')


class ProcessBridgeTestTemplateStep(models.Model):
    _name = 'process.bridge.test.template.step'
    _description = 'Process Bridge Test Template Step'
    _inherit = ['process.template.step.mixin']

    template_id = fields.Many2one('process.bridge.test.template', ondelete='cascade')


class ProcessBridgeTestTemplate(models.Model):
    """Test-only template, generating process.bridge.test.step records on a
    process.bridge.test.host anchor -- exercises process.template.mixin's
    generate_steps(), which otherwise has no test coverage anywhere in the
    repository."""
    _name = 'process.bridge.test.template'
    _description = 'Process Bridge Test Template'
    _inherit = ['process.template.mixin']

    template_step_ids = fields.One2many('process.bridge.test.template.step', 'template_id')

    def _template_step_model(self):
        return 'process.bridge.test.step'

    def _template_step_vals(self, anchor, template_step):
        return {
            'host_id': anchor.id,
            'sequence': template_step.sequence,
        }
