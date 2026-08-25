# -*- coding: utf-8 -*-
from odoo import fields, models


class WorkflowTestStep(models.Model):
    """Test-only concrete step model, playing the role a vertical's own
    step model plays for workflow.step.mixin (e.g. a freight work order).

    Deliberately lives in models/, not tests/: a model defined only inside
    a tests/ file never joins the registry (see
    shared/dispatch/models/order_bridge_test_host.py for the same
    reasoning), and workflow.step.mixin/workflow.template.step.mixin are
    AbstractModels with no concrete model of their own to test against."""
    _name = 'workflow.test.step'
    _description = 'Workflow Test Step'
    _inherit = ['workflow.step.mixin']

    host_id = fields.Many2one('workflow.test.host', ondelete='cascade')


class WorkflowTestHost(models.Model):
    """Test-only stand-in for an anchor model (trading.trade, a freight file)."""
    _name = 'workflow.test.host'
    _description = 'Workflow Test Host'
    _inherit = ['workflow.mixin']

    name = fields.Char(default='Test Host')
    step_ids = fields.One2many('workflow.test.step', 'host_id')


class WorkflowTestTemplateStep(models.Model):
    _name = 'workflow.test.template.step'
    _description = 'Workflow Test Template Step'
    _inherit = ['workflow.template.step.mixin']

    template_id = fields.Many2one('workflow.test.template', ondelete='cascade')


class WorkflowTestTemplate(models.Model):
    """Test-only template, generating workflow.test.step records on a
    workflow.test.host anchor -- exercises workflow.template.mixin's
    generate_steps(), which otherwise has no test coverage anywhere in the
    repository."""
    _name = 'workflow.test.template'
    _description = 'Workflow Test Template'
    _inherit = ['workflow.template.mixin']

    template_step_ids = fields.One2many('workflow.test.template.step', 'template_id')

    def _template_step_model(self):
        return 'workflow.test.step'

    def _template_step_vals(self, anchor, template_step):
        return {
            'host_id': anchor.id,
            'sequence': template_step.sequence,
        }
