# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestWorkflowMixin(TransactionCase):
    """Exercises has_steps, the step status transitions, and template
    generation against workflow.test.host/.step/.template (see
    shared/workflow/models/process_bridge_test_models.py) -- none of
    workflow's actual logic had any test coverage before this."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Host = cls.env['workflow.test.host']
        cls.Step = cls.env['workflow.test.step']
        cls.Template = cls.env['workflow.test.template']
        cls.TemplateStep = cls.env['workflow.test.template.step']

    def test_has_steps_false_with_no_steps(self):
        host = self.Host.create({})
        self.assertFalse(host.has_steps)

    def test_has_steps_true_once_a_step_is_added(self):
        host = self.Host.create({})
        self.Step.create({'host_id': host.id})
        self.assertTrue(host.has_steps)

    def test_step_defaults_to_draft(self):
        step = self.Step.create({})
        self.assertEqual(step.state, 'draft')

    def test_step_action_start_and_done_transitions(self):
        step = self.Step.create({})
        step.action_start()
        self.assertEqual(step.state, 'in_progress')
        step.action_done()
        self.assertEqual(step.state, 'done')

    def test_generate_steps_creates_one_step_per_template_step_on_the_anchor(self):
        host = self.Host.create({})
        template = self.Template.create({'name': 'Test Template'})
        self.TemplateStep.create([
            {'name': 'Step A', 'sequence': 20, 'template_id': template.id},
            {'name': 'Step B', 'sequence': 10, 'template_id': template.id},
        ])

        created = template.generate_steps(host)

        self.assertEqual(len(created), 2)
        self.assertEqual(host.step_ids, created)
        self.assertTrue(host.has_steps)

    def test_generate_steps_with_no_template_steps_creates_nothing(self):
        host = self.Host.create({})
        template = self.Template.create({'name': 'Empty Template'})

        created = template.generate_steps(host)

        self.assertFalse(created)
        self.assertFalse(host.has_steps)
