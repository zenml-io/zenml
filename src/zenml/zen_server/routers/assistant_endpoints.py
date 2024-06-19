#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Endpoint definitions for plugin flavors."""

import os
from typing import List
from uuid import UUID

from fastapi import APIRouter, Security
from fastapi.responses import StreamingResponse

from zenml.assistant.base_assistant import BaseAssistantHandler
from zenml.constants import (
    API,
    ASSISTANT,
    VERSION_1,
)
from zenml.enums import PluginType
from zenml.models.v2.core.assistant import AssistantRequest, AssistantResponse
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_make_call,
)
from zenml.zen_server.utils import (
    handle_exceptions,
    plugin_flavor_registry,
    zen_store,
)

assistant_router = APIRouter(
    prefix=API + VERSION_1 + ASSISTANT,
    tags=["AI"],
    responses={401: error_response, 403: error_response},
)


@assistant_router.post(
    "",
    response_model=AssistantResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def make_assistant_call(
    assistant: AssistantRequest,
    _: AuthContext = Security(authorize),
) -> AssistantResponse:
    """Makes call to the assistant.

    Args:
        assistant: Request to Assistant

    Returns:
        The created assistant.

    Raises:
        ValueError: If the plugin for the assistant is not valid.
    """
    assistant_handler = plugin_flavor_registry().get_plugin(
        name=assistant.flavor,
        _type=PluginType.ASSISTANT,
        subtype=assistant.plugin_subtype,
    )

    # Validate that the flavor and plugin_type correspond to an event source
    # implementation
    if not isinstance(assistant_handler, BaseAssistantHandler):
        raise ValueError(
            f"Assistant plugin {assistant.plugin_subtype} "
            f"for flavor {assistant.flavor} is not a valid assistant "
            "handler implementation."
        )

    return verify_permissions_and_make_call(
        request_model=assistant,
        destination_method=assistant_handler.make_assistant_call,
    )


MARKDOWN = """# Estote occulta amor aves incendia hoc lapsum

## Se rotisque gaudia

Lorem markdownum precibus amantis. Et illa. Fortibus in Romam spirandi regemque
exemplo sanguine concutiens movere? Auro quo undas arva ignaro, modo humana
effugies fusus! Genitorque inde; meo pugnacem et dicta: cito, tamen, nec iuvenis
saevi!

    it_firmware_payload(ascii_control_search(manet, gif), samba_shortcut(
            webCell, 824053) + coldGibibyteKey(paperPathLeaf),
            enterprise_smart_refresh - marginRfidSafe);
    var graphic_debug = bluSimm * 1 / pushWhoisClick + 3;
    status.ansiMirroredMail.megahertz(youtubeBlacklistKilohertz, hardWirelessTag
            * workstation);
    var bar_itunes_logic = trinitronFaqCpu;

Dumque Cecropios. *Subiectos hastile* omnes *Nebrophonosque confudit* cum mater
in somnus; pedibus. Et inde verbere praesignis crevit. Vela cum unum vipereos
quaque, vult sine **ignes**, certis imperio multi recens!

## Consumpta illic reppulit et per tellure recto

Mucrone in laudamus certus sponsa anni, viridi, vota dixerat est minus. Ista
parem videns in lingua; ibi seducunt erat, nisi, rude currus artus, in spreta
contigit. De Troum et undis et vocoque paverunt spatium supplex lux **Circes
coniuge adde**, Pallantidos tectis datis incoquit. Lelegeia manus *pisce*
narravere, ignea.

    var document_snmp = serialDesktop.memoryTebibyte(data *
            software_mysql_download, driveSnowRow.syntaxVfat(cycleSoft(
            tablet_dvd, cybersquatterTtlPlain), protector + 5, supplyHardSerial
            + smtp_pcmcia), 5 + default.transfer_and_flash(dhcp));
    var transferSurgeBaseband = -3;
    if (agp.ioSsid(heuristic(1, cloud, biometrics_surface))) {
        user_gate(syntax * 3, ultra_hot);
    } else {
        webmail_spam(circuitStandaloneTroll);
        text.unmountUs = ramArpSip;
    }
    var srgbMonitor = format_mouse - directory_formula_gui;
    host = 3;

Tu illa in, mensura Euryte illa Bacchus fortibus supple: praecordia, populandas
pectore. Liquitur educere parentis et patiar celebrant iuvenis Ammon caede nec
quippe sepulcrales eadem, in erat mandato, saepius. Sine litore feriendus
salutifer humum flenti manus totumque: mea: paelice periuria potest. Non non
tendentem [lumen](http://mutasua.org/aethera) de morique ostendit desistunt
dixerit relictum. Auris nec fratre, neque ardeat; ille sed has distantes faciam!

Enim urbis parte *genae*; bene quibus harenas Primus da felicem, magnorum. Nam
et lumina tu Procne hostis promissae, in sua ritu eadem rubefecit Iuppiter, mihi
qui parentis: sum.
"""


async def markdown_generator():
    for line in MARKDOWN.splitlines():
        yield line + "\n"


@assistant_router.get("dummy")
async def dummy(_: AuthContext = Security(authorize)):
    return StreamingResponse(
        markdown_generator(), media_type="text/event-stream"
    )


@assistant_router.post("compare-model-versions")
async def compare_model_versions(
    model_version_ids: List[UUID],
    persona: str = "",
    _: AuthContext = Security(authorize),
):
    # Fetch model versions, prepare data

    model_id = None
    versions = []
    for id_ in model_version_ids:
        model_version = (
            zen_store()
            .get_model_version(model_version_id=id_)
            .to_model_class()
        )
        versions.append(model_version)
        if model_id and model_version.model_id != model_id:
            raise ValueError("Versions don't belong to same model")

    from litellm import completion
    from litellm.types.utils import ModelResponse

    # TODO: Switch this based on persona
    prompt = "Make a haiku out of the following text:"
    # TODO: Add context here
    query = prompt

    async def _iterator():
        # Send the query to the OpenAI API
        response = completion(
            model="azure/gpt-35-turbo",
            api_base="https://zentestgpt4.openai.azure.com/",
            api_version="2024-05-01-preview",
            api_key=os.getenv("OPENAI_API_KEY"),
            messages=[{"content": query, "role": "user"}],
            max_tokens=50,
            stream=True,
        )
        for res in response:
            if isinstance(res, ModelResponse):
                if content:= res.choices[0].delta.content:
                    yield content

    return StreamingResponse(
        content=_iterator(), media_type="text/event-stream"
    )
