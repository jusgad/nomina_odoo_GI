from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import date
import base64
import json

@tagged('post_install', '-at_install')
class TestHrElectronicPayroll(TransactionCase):
    def setUp(self):
        super(TestHrElectronicPayroll, self).setUp()
        # Configuración inicial
        self.company = self.env.company
        self.company.write({
            'country_id': self.env.ref('base.co').id,
            'dian_software_id': 'TEST-SOFT-ID',
            'dian_software_pin': 'TEST-PIN',
            'dian_test_mode': True
        })

        # Crear empleado
        self.employee = self.env['hr.employee'].create({
            'name': 'Empleado NE',
            'identification_type': 'CC',
            'identification_id': '1234567890',
            'address_home_id': self.env['res.partner'].create({
                'name': 'Empleado NE',
                'email': 'empleado@test.com',
            }).id
        })

        # Crear contrato
        self.contract = self.env['hr.contract'].create({
            'name': 'Contrato NE',
            'employee_id': self.employee.id,
            'wage': 1160000.0,
            'state': 'open',
            'date_start': '2024-01-01',
            'contract_type': 'fijo',
        })

        # Crear nómina
        self.payslip = self.env['hr.payslip'].create({
            'name': 'Nómina NE',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
        })
        self.payslip.compute_sheet()
        self.payslip.action_payslip_done()

    def test_01_electronic_payroll_creation(self):
        """Prueba la creación de nómina electrónica"""
        electronic_payroll = self.env['hr.electronic.payroll'].create({
            'name': 'NE-TEST-001',
            'company_id': self.company.id,
            'payslip_ids': [(6, 0, [self.payslip.id])],
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'document_type': '102',
        })
        
        self.assertTrue(electronic_payroll, "No se creó la nómina electrónica")
        self.assertEqual(electronic_payroll.state, 'draft')

    def test_02_xml_generation(self):
        """Prueba la generación del XML"""
        electronic_payroll = self.env['hr.electronic.payroll'].create({
            'name': 'NE-TEST-002',
            'company_id': self.company.id,
            'payslip_ids': [(6, 0, [self.payslip.id])],
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'document_type': '102',
        })
        
        electronic_payroll.action_generate_xml()
        
        self.assertTrue(electronic_payroll.xml_file)
        self.assertEqual(electronic_payroll.state, 'generated')

    def test_03_xml_validation(self):
        """Prueba la validación del XML"""
        electronic_payroll = self.env['hr.electronic.payroll'].create({
            'name': 'NE-TEST-003',
            'company_id': self.company.id,
            'payslip_ids': [(6, 0, [self.payslip.id])],
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'document_type': '102',
        })
        
        electronic_payroll.action_generate_xml()
        validation_result = electronic_payroll.action_validate_xml()
        
        self.assertTrue(validation_result.get('is_valid'))

    def test_04_dian_submission(self):
        """Prueba el envío a la DIAN"""
        electronic_payroll = self.env['hr.electronic.payroll'].create({
            'name': 'NE-TEST-004',
            'company_id': self.company.id,
            'payslip_ids': [(6, 0, [self.payslip.id])],
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'document_type': '102',
        })
        
        electronic_payroll.action_generate_xml()
        electronic_payroll.action_send_dian()
        
        self.assertEqual(electronic_payroll.state, 'sent')
        self.assertTrue(electronic_payroll.dian_response)

    def test_05_adjustment_document(self):
        """Prueba la generación de documento de ajuste"""
        # Crear nómina electrónica original
        original_ne = self.env['hr.electronic.payroll'].create({
            'name': 'NE-TEST-005',
            'company_id': self.company.id,
            'payslip_ids': [(6, 0, [self.payslip.id])],
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'document_type': '102',
        })
        original_ne.action_generate_xml()
        original_ne.action_send_dian()

        # Crear documento de ajuste
        adjustment_ne = self.env['hr.electronic.payroll'].create({
            'name': 'NE-TEST-005-ADJ',
            'company_id': self.company.id,
            'payslip_ids': [(6, 0, [self.payslip.id])],
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'document_type': '103',
            'original_payroll_id': original_ne.id,
        })
        
        self.assertEqual(adjustment_ne.document_type, '103')
        self.assertTrue(adjustment_ne.original_payroll_id)

    def test_06_batch_processing(self):
        """Prueba el procesamiento por lotes"""
        # Crear otro empleado y nómina
        employee2 = self.env['hr.employee'].create({
            'name': 'Empleado NE 2',
            'identification_type': 'CC',
            'identification_id': '0987654321',
        })
        
        contract2 = self.env['hr.contract'].create({
            'name': 'Contrato NE 2',
            'employee_id': employee2.id,
            'wage': 1160000.0,
            'state': 'open',
            'date_start': '2024-01-01',
        })
        
        payslip2 = self.env['hr.payslip'].create({
            'employee_id': employee2.id,
            'contract_id': contract2.id,
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
        })
        payslip2.compute_sheet()
        payslip2.action_payslip_done()

        # Crear lote de nómina electrónica
        batch_ne = self.env['hr.electronic.payroll.batch'].create({
            'name': 'LOTE-NE-001',
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'payslip_ids': [(6, 0, [self.payslip.id, payslip2.id])],
        })
        
        batch_ne.action_process_batch()
        
        self.assertTrue(len(batch_ne.electronic_payroll_ids) > 0)

    def test_07_pdf_generation(self):
        """Prueba la generación del PDF"""
        electronic_payroll = self.env['hr.electronic.payroll'].create({
            'name': 'NE-TEST-007',
            'company_id': self.company.id,
            'payslip_ids': [(6, 0, [self.payslip.id])],
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'document_type': '102',
        })
        
        electronic_payroll.action_generate_xml()
        electronic_payroll.action_generate_pdf()
        
        self.assertTrue(electronic_payroll.pdf_file)

    def test_08_electronic_payroll_validation(self):
        """Prueba las validaciones de nómina electrónica"""
        # Intentar crear sin nóminas
        with self.assertRaises(ValidationError):
            self.env['hr.electronic.payroll'].create({
                'name': 'NE-TEST-008',
                'company_id': self.company.id,
                'date_from': '2024-01-01',
                'date_to': '2024-01-31',
                'document_type': '102',
            })

        # Intentar enviar sin generar XML
        electronic_payroll = self.env['hr.electronic.payroll'].create({
            'name': 'NE-TEST-008',
            'company_id': self.company.id,
            'payslip_ids': [(6, 0, [self.payslip.id])],
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'document_type': '102',
        })
        
        with self.assertRaises(ValidationError):
            electronic_payroll.action_send_dian()

    def test_09_cune_generation(self):
        """Prueba la generación del CUNE"""
        electronic_payroll = self.env['hr.electronic.payroll'].create({
            'name': 'NE-TEST-009',
            'company_id': self.company.id,
            'payslip_ids': [(6, 0, [self.payslip.id])],
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'document_type': '102',
        })
        
        electronic_payroll.action_generate_xml()
        
        self.assertTrue(electronic_payroll.cune)
        self.assertEqual(len(electronic_payroll.cune), 96)

    def test_10_electronic_payroll_logs(self):
        """Prueba el registro de logs"""
        electronic_payroll = self.env['hr.electronic.payroll'].create({
            'name': 'NE-TEST-010',
            'company_id': self.company.id,
            'payslip_ids': [(6, 0, [self.payslip.id])],
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
            'document_type': '102',
        })
        
        electronic_payroll.action_generate_xml()
        electronic_payroll.action_send_dian()
        
        self.assertTrue(electronic_payroll.log_ids)
        self.assertTrue(len(electronic_payroll.log_ids) >= 2)