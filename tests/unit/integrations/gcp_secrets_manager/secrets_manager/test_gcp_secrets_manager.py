from collections import namedtuple
import pytest

from zenml.integrations.gcp_secrets_manager.secrets_manager \
    .gcp_secrets_manager import remove_group_name_from_key

prepended_secret = namedtuple('prepended_secret',
                              'key_name, group_name, '
                              'expected_key, potential_error')

PREPENDED_SECRETS = [
    prepended_secret('aria_cat_age', 'aria', 'cat_age', None),
    prepended_secret('axel__cat_age', 'axel', '_cat_age', None),
    prepended_secret('kube_kube_', 'kube', 'kube_', None),
    prepended_secret('kube_kube_kube', 'kube', 'kube_kube', None),
    prepended_secret('square__square', 'square_', 'square', None),
    prepended_secret('missing_group', 'rand', None, RuntimeError),
    prepended_secret('missing_key_', 'missing_key_', None, RuntimeError),
    prepended_secret('', '', None, RuntimeError),
    prepended_secret('', 'g', None, RuntimeError),
    prepended_secret('g', '', None, RuntimeError),
]


@pytest.mark.parametrize("parametrized_input", PREPENDED_SECRETS)
def test_remove_group_name_from_key(parametrized_input: prepended_secret):
    if not parametrized_input.potential_error:
        actual_key = remove_group_name_from_key(
            key_name=parametrized_input.key_name,
            group_name=parametrized_input.group_name)

        assert actual_key == parametrized_input.expected_key
    else:
        with pytest.raises(parametrized_input.potential_error):
            remove_group_name_from_key(
                key_name=parametrized_input.key_name,
                group_name=parametrized_input.group_name)
