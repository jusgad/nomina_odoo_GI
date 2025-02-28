{
    'name': 'Nómina Colombiana',
    'version': '15.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'sequence': 38,
    'summary': 'Gestión de nómina para Colombia con todas las prestaciones y requisitos legales',
    'description': """
        Nómina Colombiana
        =================

        Este módulo implementa la gestión completa de nómina para Colombia, incluyendo:

        * Cálculo de salarios según normativa colombiana
        * Prestaciones sociales (prima, cesantías, intereses a las cesantías)
        * Vacaciones y liquidaciones
        * Horas extras y recargos
        * Incapacidades
        * Retención en la fuente
        * Generación de nómina electrónica para la DIAN
        * Planilla PILA para seguridad social
        * Certificados de ingresos y retenciones
        * Reportes legales

        Cumple con toda la normativa laboral colombiana vigente.
    """,
    'author': 'Grupo Interfase - GI',
    'website': 'https://www.grupointerfase.com.co',
    'depends': [
        'hr',
        'hr_payroll',
        'hr_holidays',
        'hr_contract',
        'hr_work_entry',
        'account',
        'l10n_co',
    ],
    'data': [
        # Seguridad
        'security/nomina_security.xml',
        'security/ir.model.access.csv',
        
        # Datos
        'data/hr_salary_rule_category_data.xml',
        'data/hr_salary_rule_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_contract_type_data.xml',
        'data/res_partner_bank_data.xml',
        
        # Vistas
        'views/hr_employee_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_run_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_electronic_payroll_views.xml',
        'views/hr_pila_views.xml',
        'views/res_config_settings_views.xml',
        'views/hr_payroll_report_views.xml',
        'views/menu_views.xml',
        
        # Asistentes
        'wizards/import_employee_wizard_views.xml',
        'wizards/hr_payroll_bank_file_wizard_views.xml',
        'wizards/hr_payroll_social_security_wizard_views.xml',
        
        # Reportes
        'reports/report_payslip_templates.xml',
        'reports/report_income_certificate.xml',
        'reports/report_severance_payment.xml',
        'reports/hr_payroll_report.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'nomina_colombia/static/src/js/**/*',
            'nomina_colombia/static/src/css/**/*',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
}