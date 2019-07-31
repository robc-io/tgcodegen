# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
from __future__ import unicode_literals

import os
import pytest
import hcl

from tgcodegen.tgcodegen import StackParser
from jinja2.exceptions import UndefinedError, TemplateSyntaxError

from pprint import pprint


RENDER_FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'templates')

SINGLE_STACK = {0: {'region': 'ap-northeast-1',
                    'modules': {
                        'vpc': {'type': 'module',
                                'source': 'github.com/terraform-aws-modules/terraform-aws-vpc.git?ref=v1.59.0',
                                'dependencies': '',
                                'vars': {'name': 'vpc-dev', 'enable_nat_gateway': False, 'single_nat_gateway': False,
                                         'enable_dns_hostnames': True, 'enable_dns_support': True}},
                        'keys': {'type': 'module',
                                 'source': 'github.com/robcxyz/terragrunt-root-modules.git//common/keys',
                                 'dependencies': [''], 'vars': {'name': 'keys'}},
                        'security_groups': {'type': 'module',
                                            'source': 'github.com/robcxyz/terragrunt-root-modules.git//common/keys',
                                            'dependencies': [''], 'vars': {'name': 'security_groups'}},
                        'ec2': {'type': 'module', 'source': 'github.com/{ git_user }/{ repo }.git//{{ module_path }}',
                                'dependencies': '{ dependencies }', 'vars': {'name': 'ec2'}},
                        'ebs': {'type': 'module', 'source': '', 'dependencies': '', 'vars': {}},
                        'logging': {'type': 'module', 'source': '', 'dependencies': '', 'vars': {}}}, 'files': {}}}

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'stacks')

# Name, valid or not valid boolean
STACK_FIXTURES = [
    (
        "common.hcl",
        False,
    ),
    # (
    #     "common-render.hcl",
    #     False,
    # ),
    (
        "basic-p-rep.hcl",
        False,
    ),
    (
        "bad-hcl.hcl",
        True,
    ),
    (
        "bad-common.hcl",
        True,
    )
]

# Name, valid or not valid boolean
HEAD_FIXTURES = [
    (
        "head",
        False
    ),
    (
        "bad-head",
        True,
    )
]

SERVICE_FIXTURES = [
    (
        "service",
        False
    ),
    (
        "bad-service",
        True,
    )
]

VERSION_FIXTURES = [
    "0.12", "0.11"
]


@pytest.mark.parametrize("hcl_fname,invalid", STACK_FIXTURES)
def test_stack_parser(hcl_fname, invalid):
    with open(os.path.join(FIXTURE_DIR, hcl_fname), 'rb') as fp:
        print(f'hcl_fname is {hcl_fname}')
        inp = fp.read()

        if hcl_fname not in ['common-render.hcl']:

            if not invalid:
                output = StackParser(hcl.loads(inp)).stack
                pprint(output)
            else:
                with pytest.raises(ValueError):
                    StackParser(hcl.loads(inp))


@pytest.mark.parametrize("stack_file,stack_invalid", STACK_FIXTURES)
@pytest.mark.parametrize("service_file,service_invalid", SERVICE_FIXTURES)
@pytest.mark.parametrize("head_file,head_invalid", HEAD_FIXTURES)
@pytest.mark.parametrize("version", VERSION_FIXTURES)
def test_make_all(stack_file, stack_invalid, service_file, service_invalid, head_file, head_invalid, version,
                  tmpdir):

    # inputs = ['']
    # input_generator = (i for i in inputs)
    # monkeypatch.setattr('builtins.input', lambda prompt: next(input_generator))

    tg = TerragruntGenerator(debug=True, terraform_version=version, headless=True)
    tg.templates_dir = RENDER_FIXTURE_DIR
    tg.stacks_dir = FIXTURE_DIR

    tg.ask_terragrunt_version()

    tg.head_template = head_file + tg.terraform_version + '.hcl'
    tg.service_template = service_file + tg.terraform_version + '.hcl'
    p = tmpdir.mkdir("sub")
    os.chdir(p)
    print(f'Cur dir is {tg.templates_dir}')
    with open(os.path.join(FIXTURE_DIR, stack_file), 'r') as fp:
        print(f'\n\ntpl_fname is {service_file}\n\n')
        if not stack_invalid:
            print(f'f{stack_file} stack is valid')
            inp = hcl.load(fp)
            tg.region = 'ap-northeast-1'
            tg.stack[0] = StackParser(inp).stack
            tg.stack[0].update({'region': 'ap-northeast-1'})
            if not service_invalid and not head_invalid:
                print(f'{service_file} and {head_file} is valid')
                tg.make_all()

                if int(tg.terraform_version) == 12:
                    print(f'version = {version}')
                    print(os.listdir(p))
                    assert os.listdir(p) == sorted(['ap-northeast-1', 'environment.tfvars',
                                                    'terragrunt.hcl', 'clear-cache.sh',
                                                    'stack.json'])
                    with open(os.path.join(p,'ap-northeast-1', 'region.tfvars')) as fp:
                        print(fp.read())
                elif int(tg.terraform_version) == 11:
                    print(f'version = {version}')
                    print(os.listdir(p))
                    assert sorted(os.listdir(p)) == sorted(['ap-northeast-1', 'environment.tfvars',
                                                            'terraform.tfvars', 'clear-cache.sh',
                                                            'stack.json'])
                    with open(os.path.join(p,'ap-northeast-1', 'region.tfvars')) as fp:
                        print(fp.read())

                else:
                    print(tg.terraform_version)
                    print(os.listdir(os.path.join(p)))
                    raise UndefinedError
            # Check that errors are raised
            elif service_invalid and not head_invalid:
                with pytest.raises((ValueError, UndefinedError, TemplateSyntaxError)):
                    print(f'version = {version}')
                    print(f'Service file = {tg.service_template} is invalid ')
                    tg.make_all()
            elif head_invalid and not service_invalid:
                with pytest.raises((ValueError, UndefinedError, TemplateSyntaxError)):
                    print(f'version = {version}')
                    print(f'Service file = {tg.service_template} is {service_invalid}' +
                          f' and Head file = {tg.head_template} is {head_invalid}')
                    tg.get_tpl_env()
                    tg.make_head()
            elif head_invalid and service_invalid:
                with pytest.raises((ValueError, UndefinedError, TemplateSyntaxError)):
                    print(f'version = {version}')
                    print(f'Service file = {tg.service_template} is {service_invalid}' +
                          f' and Head file = {tg.head_template} is {head_invalid}')
                    tg.make_all()

        else:
            with pytest.raises((ValueError, KeyError)):
                tg.make_all()
