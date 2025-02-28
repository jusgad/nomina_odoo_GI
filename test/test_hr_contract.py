from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta

@tagged('post_install', '-at_install')
class TestHrContract(TransactionCase):
    def setUp(self):
        super(TestHrContract, self).setUp()
        # Configuración inicial
        self.company = self.env.company
        self.company.country_id = self.env.ref('base.co')

        # Crear empleado de prueba
        self.employee = self.env['hr.employee'].create({
            'name': 'Empleado Test Contrato',
            'identification_type': 'CC',
            'identification_id': '1234567890',
            'gender': 'male',
            'birthday': '1990-01-01',
        })

    def test_01_contract_creation(self):
        """Prueba la creación de contratos"""
        contract = self.env['hr.contract'].create({
            'name': 'Contrato Test',
            'employee_id': self.employee.id,
            'wage': 1160000.0,  # SMLV 2024
            'state': 'draft',
            'date_start': '2024-01-01',
            'contract_type': 'fijo',
            'wage_type': 'ordinary',
            'transport_allowance': True,
        })
        
        self.assertTrue(contract, "No se creó el contrato")
        self.assertEqual(contract.state, 'draft')

    def test_02_contract_validation(self):
        """Prueba las validaciones del contrato"""
        with self.assertRaises(ValidationError):
            self.env['hr.contract'].create({
                'name': 'Contrato Inválido',
                'employee_id': self.employee.id,
                'wage': 0,  # Salario inválido
                'date_start': '2024-01-01',
            })

    def test_03_contract_wage_constraints(self):
        """Prueba las restricciones de salario"""
        contract = self.env['hr.contract'].create({
            'name': 'Contrato Salario',
            'employee_id': self.employee.id,
            'wage': 1160000.0,
            'date_start': '2024-01-01',
            'contract_type': 'fijo',
        })

        # Probar cambio a salario integral
        contract.wage_type = 'integral'
        self.assertTrue(contract.wage >= 1160000.0 * 13)

    def test_04_contract_dates(self):
        """Prueba las validaciones de fechas"""
        contract = self.env['hr.contract'].create({
            'name': 'Contrato Fechas',
            'employee_id': self.employee.id,
            'wage': 1160000.0,
            'date_start': '2024-01-01',
            'date_end': '2024-12-31',
            'contract_type': 'fijo',
        })

        # Verificar duración del contrato
        duration = contract._get_contract_duration()
        self.assertEqual(duration, 12)

    def test_05_contract_benefits(self):
        """Prueba los beneficios del contrato"""
        contract = self.env['hr.contract'].create({
            'name': 'Contrato Beneficios',
            'employee_id': self.employee.id,
            'wage': 1160000.0,
            'date_start': '2024-01-01',
            'contract_type': 'fijo',
            'transport_allowance': True,
        })

        # Verificar auxilio de transporte
        self.assertTrue(contract.transport_allowance_amount > 0)

    def test_06_contract_state_changes(self):
        """Prueba los cambios de estado del contrato"""
        contract = self.env['hr.contract'].create({
            'name': 'Contrato Estados',
            'employee_id': self.employee.id,
            'wage': 1160000.0,
            'date_start': '2024-01-01',
            'contract_type': 'fijo',
        })

        # Probar flujo de estados
        contract.state = 'open'
        self.assertEqual(contract.state, 'open')
        
        contract.state = 'close'
        self.assertEqual(contract.state, 'close')

    def test_07_contract_type_constraints(self):
        """Prueba las restricciones por tipo de contrato"""
        # Contrato a término fijo
        contract_fijo = self.env['hr.contract'].create({
            'name': 'Contrato Fijo',
            'employee_id': self.employee.id,
            'wage': 1160000.0,
            'date_start': '2024-01-01',
            'date_end': '2024-12-31',
            'contract_type': 'fijo',
        })
        self.assertTrue(contract_fijo.date_end)

        # Contrato indefinido
        contract_indef = self.env['hr.contract'].create({
            'name': 'Contrato Indefinido',
            'employee_id': self.employee.id,
            'wage': 1160000.0,
            'date_start': '2024-01-01',
            'contract_type': 'indefinido',
        })
        self.assertFalse(contract_indef.date_end)

    def test_08_contract_risk_class(self):
        """Prueba la clase de riesgo ARL"""
        contract = self.env['hr.contract'].create({
            'name': 'Contrato Riesgo',
            'employee_id': self.employee.id,
            'wage': 1160000.0,
            'date_start': '2024-01-01',
            'contract_type': 'fijo',
            'risk_class': '1',
        })

        # Verificar tasa de ARL según clase de riesgo
        self.assertEqual(contract.arl_rate, 0.522)

    def test_09_contract_trial_period(self):
        """Prueba el período de prueba"""
        contract = self.env['hr.contract'].create({
            'name': 'Contrato Prueba',
            'employee_id': self.employee.id,
            'wage': 1160000.0,
            'date_start': '2024-01-01',
            'contract_type': 'fijo',
            'trial_period': True,
            'trial_period_duration': 2,
        })

        # Verificar fecha fin período de prueba
        expected_end = date(2024, 3, 1)
        self.assertEqual(contract.trial_period_end_date, expected_end)

    def test_10_contract_wage_changes(self):
        """Prueba los cambios de salario"""
        contract = self.env['hr.contract'].create({
            'name': 'Contrato Cambio Salario',
            'employee_id': self.employee.id,
            'wage': 1160000.0,
            'date_start': '2024-01-01',
            'contract_type': 'fijo',
        })

        # Registrar histórico de cambios de salario
        contract.wage = 1200000.0
        wage_history = self.env['hr.contract.wage.history'].search([
            ('contract_id', '=', contract.id)
        ])
        self.assertTrue(wage_history)
        self.assertEqual(len(wage_history), 1)