from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta

@tagged('post_install', '-at_install')
class TestHrPayslip(TransactionCase):
    def setUp(self):
        super(TestHrPayslip, self).setUp()
        # Configuración inicial
        self.company = self.env.company
        self.company.country_id = self.env.ref('base.co')

        # Crear empleado
        self.employee = self.env['hr.employee'].create({
            'name': 'Empleado Test Nómina',
            'identification_type': 'CC',
            'identification_id': '1234567890',
        })

        # Crear contrato
        self.contract = self.env['hr.contract'].create({
            'name': 'Contrato Test',
            'employee_id': self.employee.id,
            'wage': 1160000.0,
            'state': 'open',
            'date_start': '2024-01-01',
            'contract_type': 'fijo',
        })

    def test_01_payslip_creation(self):
        """Prueba la creación de nómina"""
        payslip = self.env['hr.payslip'].create({
            'name': 'Nómina Test',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
        })
        
        self.assertTrue(payslip, "No se creó la nómina")
        self.assertEqual(payslip.state, 'draft')

    def test_02_payslip_computation(self):
        """Prueba el cálculo de nómina"""
        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
        })
        
        payslip.compute_sheet()
        
        # Verificar líneas básicas
        basic_line = payslip.line_ids.filtered(lambda l: l.code == 'BASIC')
        self.assertEqual(basic_line.total, 1160000.0)

        # Verificar deducciones
        health_line = payslip.line_ids.filtered(lambda l: l.code == 'HEALTH')
        self.assertEqual(health_line.total, -46400.0)  # 4% de 1160000

    def test_03_overtime_calculation(self):
        """Prueba el cálculo de horas extra"""
        # Crear entrada de trabajo para horas extra
        self.env['hr.work.entry'].create({
            'name': 'Horas Extra',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_start': '2024-01-01 08:00:00',
            'date_stop': '2024-01-01 12:00:00',
            'work_entry_type_id': self.env.ref('nomina_colombia.work_entry_type_hed_col').id,
        })

        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
        })
        
        payslip.compute_sheet()
        
        # Verificar línea de horas extra
        he_line = payslip.line_ids.filtered(lambda l: l.code == 'HED')
        self.assertTrue(he_line.total > 0)

    def test_04_leave_integration(self):
        """Prueba la integración con ausencias"""
        # Crear ausencia
        leave = self.env['hr.leave'].create({
            'name': 'Vacaciones',
            'employee_id': self.employee.id,
            'holiday_status_id': self.env.ref('hr_holidays.holiday_status_vac').id,
            'date_from': '2024-01-15 07:00:00',
            'date_to': '2024-01-19 17:00:00',
        })
        leave.action_approve()

        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
        })
        
        payslip.compute_sheet()
        
        # Verificar línea de vacaciones
        vac_line = payslip.line_ids.filtered(lambda l: l.code == 'VAC')
        self.assertTrue(vac_line)

    def test_05_payslip_validation(self):
        """Prueba las validaciones de nómina"""
        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
        })
        
        payslip.compute_sheet()
        payslip.action_payslip_done()
        
        # Verificar estado
        self.assertEqual(payslip.state, 'done')
        
        # Verificar que no se puede modificar
        with self.assertRaises(ValidationError):
            payslip.write({'date_from': '2024-01-02'})

    def test_06_payslip_refund(self):
        """Prueba el reembolso de nómina"""
        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
        })
        
        payslip.compute_sheet()
        payslip.action_payslip_done()
        
        # Crear reembolso
        refund_payslip = payslip.refund_sheet()
        self.assertTrue(refund_payslip)
        self.assertEqual(refund_payslip.credit_note, True)

    def test_07_payslip_batch(self):
        """Prueba el procesamiento por lotes"""
        # Crear otro empleado y contrato
        employee2 = self.env['hr.employee'].create({
            'name': 'Empleado Test 2',
            'identification_type': 'CC',
            'identification_id': '0987654321',
        })
        
        contract2 = self.env['hr.contract'].create({
            'name': 'Contrato Test 2',
            'employee_id': employee2.id,
            'wage': 1160000.0,
            'state': 'open',
            'date_start': '2024-01-01',
            'contract_type': 'fijo',
        })

        # Crear lote de nómina
        batch = self.env['hr.payslip.run'].create({
            'name': 'Lote Test',
            'date_start': '2024-01-01',
            'date_end': '2024-01-31',
        })
        
        # Generar nóminas
        batch.generate_payslips()
        
        self.assertEqual(len(batch.slip_ids), 2)

    def test_08_payslip_inputs(self):
        """Prueba las entradas de nómina"""
        # Crear entrada
        input_type = self.env['hr.payslip.input.type'].create({
            'name': 'Bono',
            'code': 'BONUS',
        })

        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
        })
        
        # Agregar entrada
        self.env['hr.payslip.input'].create({
            'payslip_id': payslip.id,
            'input_type_id': input_type.id,
            'amount': 100000.0,
        })
        
        payslip.compute_sheet()
        
        # Verificar línea de bono
        bonus_line = payslip.line_ids.filtered(lambda l: l.code == 'BONUS')
        self.assertEqual(bonus_line.total, 100000.0)