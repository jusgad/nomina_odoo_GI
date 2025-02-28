from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

@tagged('post_install', '-at_install')
class TestNominaColombia(TransactionCase):
    def setUp(self):
        super(TestNominaColombia, self).setUp()
        # Configuración básica para todas las pruebas
        self.company = self.env.company
        self.company.country_id = self.env.ref('base.co')
        
        # Crear datos de prueba
        self._create_test_data()

    def _create_test_data(self):
        # Crear empleado de prueba
        self.employee = self.env['hr.employee'].create({
            'name': 'Empleado Prueba',
            'identification_type': 'CC',
            'identification_id': '1234567890',
            'gender': 'male',
            'birthday': '1990-01-01',
        })

        # Crear contrato de prueba
        self.contract = self.env['hr.contract'].create({
            'name': 'Contrato Prueba',
            'employee_id': self.employee.id,
            'wage': 1000000.0,
            'state': 'open',
            'date_start': '2023-01-01',
            'contract_type': 'fijo',
            'wage_type': 'ordinary',
        })

    def test_01_contract_validation(self):
        """Prueba la validación de contratos"""
        with self.assertRaises(ValidationError):
            self.contract.wage = 0

    def test_02_payslip_computation(self):
        """Prueba el cálculo de nómina"""
        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': '2023-01-01',
            'date_to': '2023-01-31',
        })
        payslip.compute_sheet()
        
        # Verificar resultados
        self.assertTrue(payslip.line_ids, "No se generaron líneas de nómina")
        basic_line = payslip.line_ids.filtered(lambda l: l.code == 'BASIC')
        self.assertEqual(basic_line.total, 1000000.0)

    def test_03_provision_calculation(self):
        """Prueba el cálculo de provisiones"""
        wizard = self.env['hr.payroll.provision.wizard'].create({
            'date_from': '2023-01-01',
            'date_to': '2023-01-31',
            'provision_types': 'all',
        })
        
        provisions = wizard._calculate_provisions(self.employee)
        self.assertTrue(provisions, "No se calcularon provisiones")

    def test_04_pila_generation(self):
        """Prueba la generación de PILA"""
        pila = self.env['hr.pila'].create({
            'date_from': '2023-01-01',
            'date_to': '2023-01-31',
            'payment_date': '2023-02-05',
        })
        pila.action_generate_file()
        
        self.assertTrue(pila.file_data, "No se generó el archivo PILA")

    def test_05_electronic_payroll(self):
        """Prueba la generación de nómina electrónica"""
        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': '2023-01-01',
            'date_to': '2023-01-31',
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()
        
        wizard = self.env['hr.payroll.electronic.wizard'].create({
            'payslip_run_id': payslip.payslip_run_id.id,
            'date_from': '2023-01-01',
            'date_to': '2023-01-31',
        })
        
        result = wizard.action_generate_electronic_payroll()
        self.assertTrue(result, "No se generó la nómina electrónica")

    def test_06_severance_payment(self):
        """Prueba la liquidación de cesantías"""
        severance = self.env['hr.severance.payment'].create({
            'employee_id': self.employee.id,
            'date_from': '2023-01-01',
            'date_to': '2023-12-31',
        })
        severance.calculate_severance()
        
        self.assertTrue(severance.severance_amount > 0, "No se calculó el monto de cesantías")
        self.assertTrue(severance.interest_amount > 0, "No se calcularon los intereses")

    def test_07_payroll_reports(self):
        """Prueba los reportes de nómina"""
        report = self.env['hr.payroll.report'].read_group(
            domain=[],
            fields=['basic_wage:sum', 'net_wage:sum'],
            groupby=['date_from:month']
        )
        self.assertTrue(report, "No se generaron datos para el reporte")