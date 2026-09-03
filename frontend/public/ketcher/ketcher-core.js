/****************************************************************************
 * Copyright 2021 EPAM Systems
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 ***************************************************************************/
'use strict';

Object.defineProperty(exports, '__esModule', { value: true });

var elementColor = require('./domain/constants/elementColor.js');
var elements = require('./domain/constants/elements.js');
var element_types = require('./domain/constants/element.types.js');
var generics = require('./domain/constants/generics.js');
var image = require('./domain/constants/image.js');
var multitailArrow = require('./domain/constants/multitailArrow.js');
var chains = require('./domain/constants/chains.js');
var monomers = require('./domain/constants/monomers.js');
var layout = require('./domain/constants/layout.js');
var atom = require('./domain/entities/atom.js');
var atomList = require('./domain/entities/atomList.js');
var bond = require('./domain/entities/bond.js');
var fixedPrecision = require('./domain/entities/fixedPrecision.js');
var fragment = require('./domain/entities/fragment.js');
var functionalGroup = require('./domain/entities/functionalGroup.js');
var halfBond = require('./domain/entities/halfBond.js');
var loop = require('./domain/entities/loop.js');
var rgroup = require('./domain/entities/rgroup.js');
var rgroupAttachmentPoint = require('./domain/entities/rgroupAttachmentPoint.js');
var rxnArrow = require('./domain/entities/rxnArrow.js');
var rxnPlus = require('./domain/entities/rxnPlus.js');
var sgroup = require('./domain/entities/sgroup.js');
var sgroupForest = require('./domain/entities/sgroupForest.js');
var simpleObject = require('./domain/entities/simpleObject.js');
var struct = require('./domain/entities/struct.js');
var text = require('./domain/entities/text.js');
var pile = require('./domain/entities/pile.js');
var vec2 = require('./domain/entities/vec2.js');
var box2Abs = require('./domain/entities/box2Abs.js');
var pool = require('./domain/entities/pool.js');
var image$1 = require('./domain/entities/image.js');
var multitailArrow$1 = require('./domain/entities/multitailArrow.js');
var highlight = require('./domain/entities/highlight.js');
var sGroupAttachmentPoint = require('./domain/entities/sGroupAttachmentPoint.js');
var monomerMicromolecule = require('./domain/entities/monomerMicromolecule.js');
var Peptide = require('./domain/entities/Peptide.js');
var BaseMonomer = require('./domain/entities/BaseMonomer.js');
var Chem = require('./domain/entities/Chem.js');
var Sugar = require('./domain/entities/Sugar.js');
var RNABase = require('./domain/entities/RNABase.js');
var Phosphate = require('./domain/entities/Phosphate.js');
var Axis = require('./domain/entities/Axis.js');
var Nucleoside = require('./domain/entities/Nucleoside.js');
var Nucleotide = require('./domain/entities/Nucleotide.js');
var types = require('./domain/entities/monomer-chains/types.js');
var Chain = require('./domain/entities/monomer-chains/Chain.js');
var ChainsCollection = require('./domain/entities/monomer-chains/ChainsCollection.js');
var MonomerSequenceNode = require('./domain/entities/MonomerSequenceNode.js');
var EmptySequenceNode = require('./domain/entities/EmptySequenceNode.js');
var LinkerSequenceNode = require('./domain/entities/LinkerSequenceNode.js');
var UnresolvedMonomer = require('./domain/entities/UnresolvedMonomer.js');
var UnsplitNucleotide = require('./domain/entities/UnsplitNucleotide.js');
var PolymerBond = require('./domain/entities/PolymerBond.js');
var AmbiguousMonomer = require('./domain/entities/AmbiguousMonomer.js');
var MonomerToAtomBond = require('./domain/entities/MonomerToAtomBond.js');
var HydrogenBond = require('./domain/entities/HydrogenBond.js');
var SGroupDrawingEntity = require('./domain/entities/SGroupDrawingEntity.js');
var BackBoneSequenceNode = require('./domain/entities/BackBoneSequenceNode.js');
var DrawingEntitiesManager_replaceMonomer = require('./domain/entities/DrawingEntitiesManager.replaceMonomer.js');
var Command = require('./domain/entities/Command.js');
var CoreAtom = require('./domain/entities/CoreAtom.js');
var CoreStereoFlag = require('./domain/entities/CoreStereoFlag.js');
var ketSerializer = require('./domain/serializers/ket/ketSerializer.js');
var helpers = require('./domain/serializers/ket/helpers.js');
var molSerializer = require('./domain/serializers/mol/molSerializer.js');
var sdfSerializer = require('./domain/serializers/sdf/sdfSerializer.js');
var structService_types = require('./domain/services/struct/structService.types.js');
var scale = require('./domain/helpers/scale.js');
var stereoValidator = require('./domain/helpers/stereoValidator.js');
var functionalGroupsProvider = require('./domain/helpers/functionalGroupsProvider.js');
var saltsAndSolventsProvider = require('./domain/helpers/saltsAndSolventsProvider.js');
var attachmentPointCalculations = require('./domain/helpers/attachmentPointCalculations.js');
var monomers$1 = require('./domain/types/monomers.js');
var entities = require('./domain/types/entities.js');
var remoteStructService = require('./infrastructure/services/struct/remoteStructService.js');
var remoteStructServiceProvider = require('./infrastructure/services/struct/remoteStructServiceProvider.js');
var helpers$1 = require('./infrastructure/services/helpers.js');
var supportedFormatProperties = require('./application/formatters/supportedFormatProperties.js');
var formatProperties = require('./application/formatters/formatProperties.js');
var structFormatter_types = require('./application/formatters/structFormatter.types.js');
var formatterFactory = require('./application/formatters/formatterFactory.js');
var identifyStructFormat = require('./application/formatters/identifyStructFormat.js');
var constants = require('./application/formatters/constants.js');
var ket = require('./application/formatters/types/ket.js');
var renderStruct = require('./application/render/renderStruct.js');
var raphaelRender = require('./application/render/raphaelRender.js');
var reobject = require('./application/render/restruct/reobject.js');
var reatom = require('./application/render/restruct/reatom.js');
var rebond = require('./application/render/restruct/rebond.js');
var reenhancedFlag = require('./application/render/restruct/reenhancedFlag.js');
var refrag = require('./application/render/restruct/refrag.js');
var rergroup = require('./application/render/restruct/rergroup.js');
var rerxnarrow = require('./application/render/restruct/rerxnarrow.js');
var rerxnplus = require('./application/render/restruct/rerxnplus.js');
var resgroup = require('./application/render/restruct/resgroup.js');
var resimpleObject = require('./application/render/restruct/resimpleObject.js');
var restruct = require('./application/render/restruct/restruct.js');
var retext = require('./application/render/restruct/retext.js');
var visel = require('./application/render/restruct/visel.js');
var generalEnumTypes = require('./application/render/restruct/generalEnumTypes.js');
var showHydrogenLabels = require('./application/render/restruct/showHydrogenLabels.js');
var rergroupAttachmentPoint = require('./application/render/restruct/rergroupAttachmentPoint.js');
var reImage = require('./application/render/restruct/reImage.js');
var remultitailArrow = require('./application/render/restruct/remultitailArrow.js');
var draftToLexical = require('./application/render/restruct/draftToLexical.js');
var BaseRenderer = require('./application/render/renderers/BaseRenderer.js');
var BaseMonomerRenderer = require('./application/render/renderers/BaseMonomerRenderer.js');
var ChemRenderer = require('./application/render/renderers/ChemRenderer.js');
var PeptideRenderer = require('./application/render/renderers/PeptideRenderer.js');
var PhosphateRenderer = require('./application/render/renderers/PhosphateRenderer.js');
var SugarRenderer = require('./application/render/renderers/SugarRenderer.js');
var RNABaseRenderer = require('./application/render/renderers/RNABaseRenderer.js');
var UnresolvedMonomerRenderer = require('./application/render/renderers/UnresolvedMonomerRenderer.js');
var UnsplitNucleotideRenderer = require('./application/render/renderers/UnsplitNucleotideRenderer.js');
var AmbiguousMonomerRenderer = require('./application/render/renderers/AmbiguousMonomerRenderer.js');
var SGroupRenderer = require('./application/render/renderers/SGroupRenderer.js');
var RenderersManager = require('./application/render/renderers/RenderersManager.js');
var utils = require('./application/render/renderers/utils.js');
var StereoFlagRenderer = require('./application/render/renderers/StereoFlagRenderer.js');
var SequenceRenderer = require('./application/render/renderers/sequence/SequenceRenderer.js');
var BaseSequenceItemRenderer = require('./application/render/renderers/sequence/BaseSequenceItemRenderer.js');
var BackBoneBondSequenceRenderer = require('./application/render/renderers/sequence/BackBoneBondSequenceRenderer.js');
var BaseSequenceRenderer = require('./application/render/renderers/sequence/BaseSequenceRenderer.js');
var ChemSequenceItemRenderer = require('./application/render/renderers/sequence/ChemSequenceItemRenderer.js');
var EmptySequenceItemRenderer = require('./application/render/renderers/sequence/EmptySequenceItemRenderer.js');
var NucleotideSequenceItemRenderer = require('./application/render/renderers/sequence/NucleotideSequenceItemRenderer.js');
var NucleosideSequenceItemRenderer = require('./application/render/renderers/sequence/NucleosideSequenceItemRenderer.js');
var PeptideSequenceItemRenderer = require('./application/render/renderers/sequence/PeptideSequenceItemRenderer.js');
var PhosphateSequenceItemRenderer = require('./application/render/renderers/sequence/PhosphateSequenceItemRenderer.js');
var PolymerBondSequenceRenderer = require('./application/render/renderers/sequence/PolymerBondSequenceRenderer.js');
var RNASequenceItemRenderer = require('./application/render/renderers/sequence/RNASequenceItemRenderer.js');
var SequenceNodeRendererFactory = require('./application/render/renderers/sequence/SequenceNodeRendererFactory.js');
var UnresolvedMonomerSequenceItemRenderer = require('./application/render/renderers/sequence/UnresolvedMonomerSequenceItemRenderer.js');
var UnsplitNucleotideSequenceItemRenderer = require('./application/render/renderers/sequence/UnsplitNucleotideSequenceItemRenderer.js');
var coordinateTransformation = require('./application/render/coordinateTransformation.js');
var scrollbarContainer = require('./application/render/scrollbar/scrollbar-container.js');
var notifyRenderComplete = require('./application/render/notifyRenderComplete.js');
var options = require('./application/render/options.js');
var render_types = require('./application/render/render.types.js');
var index = require('./application/editor/index.js');
var ketcher = require('./application/ketcher.js');
var ketcher_types = require('./application/ketcher.types.js');
var ketcherBuilder = require('./application/ketcherBuilder.js');
var types$2 = require('./application/settings/types.js');
var SettingsService = require('./application/settings/SettingsService.js');
var LocalStorageAdapter = require('./application/settings/LocalStorageAdapter.js');
var MemoryStorageAdapter = require('./application/settings/MemoryStorageAdapter.js');
var SchemaValidator = require('./application/settings/SchemaValidator.js');
var SettingsMigration = require('./application/settings/SettingsMigration.js');
var schema = require('./application/settings/schema.js');
var settingsFormatters = require('./application/settings/settingsFormatters.js');
var utils$2 = require('./application/utils.js');
var ketcherProvider = require('./application/ketcherProvider.js');
var getStructure = require('./application/getStructure.js');
var monomers$2 = require('./domain/helpers/monomers.js');
var ifDef = require('./utilities/ifDef.js');
var toFixed = require('./utilities/toFixed.js');
var runAsyncAction = require('./utilities/runAsyncAction.js');
var b64toBlob = require('./utilities/b64toBlob.js');
var notifyRequestCompleted = require('./utilities/notifyRequestCompleted.js');
var KetcherLogger = require('./utilities/KetcherLogger.js');
var SettingsManager = require('./utilities/SettingsManager.js');
var keynorm = require('./utilities/keynorm.js');
var shortcutsUtil = require('./utilities/shortcutsUtil.js');
var clipboardUtils = require('./utilities/clipboardUtils.js');
var getSvgFromDrawnStructures = require('./utilities/getSvgFromDrawnStructures.js');
var ensureString = require('./utilities/ensureString.js');
var normalizeError = require('./utilities/normalizeError.js');
var monomers$3 = require('./utilities/monomers.js');
var dom = require('./utilities/dom.js');
var render_constants = require('./application/render/render.constants.js');
var AtomAttr = require('./application/editor/operations/atom/AtomAttr.js');
var AtomMove = require('./application/editor/operations/atom/AtomMove.js');
var AtomAdd = require('./application/editor/operations/atom/AtomAdd.js');
var AtomDelete = require('./application/editor/operations/atom/AtomDelete.js');
var BondAttr = require('./application/editor/operations/bond/BondAttr.js');
var BondMove = require('./application/editor/operations/bond/BondMove.js');
var BondAdd = require('./application/editor/operations/bond/BondAdd.js');
var BondDelete = require('./application/editor/operations/bond/BondDelete.js');
var CanvasLoad = require('./application/editor/operations/CanvasLoad.js');
var AlignDescriptors = require('./application/editor/operations/AlignDescriptors.js');
var RestoreDescriptorsPosition = require('./application/editor/operations/RestoreDescriptorsPosition.js');
var EnhancedFlagMove = require('./application/editor/operations/EnhancedFlagMove.js');
var EnhancedFlagClear = require('./application/editor/operations/EnhancedFlagClear.js');
var UpdateIfThen = require('./application/editor/operations/UpdateIfThen.js');
var RestoreIfThen = require('./application/editor/operations/RestoreIfThen.js');
var FragmentAdd = require('./application/editor/operations/FragmentAdd.js');
var FragmentDelete = require('./application/editor/operations/FragmentDelete.js');
var FragmentSetProperties = require('./application/editor/operations/FragmentSetProperties.js');
var FragmentAddStereoAtom = require('./application/editor/operations/FragmentAddStereoAtom.js');
var FragmentDeleteStereoAtom = require('./application/editor/operations/FragmentDeleteStereoAtom.js');
var FragmentStereoFlag = require('./application/editor/operations/FragmentStereoFlag.js');
var calcimplicitH = require('./application/editor/operations/calcimplicitH.js');
var LoopMove = require('./application/editor/operations/LoopMove.js');
var OperationType = require('./application/editor/operations/OperationType.js');
var imageMove = require('./application/editor/operations/image/imageMove.js');
var imageResize = require('./application/editor/operations/image/imageResize.js');
var imageUpsertDelete = require('./application/editor/operations/image/imageUpsertDelete.js');
var multitailArrowAddRemoveTail = require('./application/editor/operations/multitailArrow/multitailArrowAddRemoveTail.js');
var multitailArrowMove = require('./application/editor/operations/multitailArrow/multitailArrowMove.js');
var multitailArrowMoveHeadTail = require('./application/editor/operations/multitailArrow/multitailArrowMoveHeadTail.js');
var multitailArrowResizeTailHead = require('./application/editor/operations/multitailArrow/multitailArrowResizeTailHead.js');
var multitailArrowUpsertDelete = require('./application/editor/operations/multitailArrow/multitailArrowUpsertDelete.js');
var RGroupAttr = require('./application/editor/operations/rgroup/RGroupAttr.js');
var RGroupFragment = require('./application/editor/operations/rgroup/RGroupFragment.js');
var RGroupAttachmentPointAdd = require('./application/editor/operations/rgroupAttachmentPoint/RGroupAttachmentPointAdd.js');
var RGroupAttachmentPointRemove = require('./application/editor/operations/rgroupAttachmentPoint/RGroupAttachmentPointRemove.js');
var RxnArrowMove = require('./application/editor/operations/rxn/RxnArrowMove.js');
var RxnArrowRotate = require('./application/editor/operations/rxn/RxnArrowRotate.js');
var RxnArrowResize = require('./application/editor/operations/rxn/RxnArrowResize.js');
var RxnPlusMove = require('./application/editor/operations/rxn/plus/RxnPlusMove.js');
var index$2 = require('./application/editor/operations/rxn/plus/index.js');
var index$1 = require('./application/editor/operations/rxn/index.js');
var simpleObject$1 = require('./application/editor/operations/simpleObject.js');
var sgroupAtom = require('./application/editor/operations/sgroup/sgroupAtom.js');
var SGroupAttr = require('./application/editor/operations/sgroup/SGroupAttr.js');
var SGroupDataMove = require('./application/editor/operations/sgroup/SGroupDataMove.js');
var sgroupHierarchy = require('./application/editor/operations/sgroup/sgroupHierarchy.js');
var sgroupAttachmentPoints = require('./application/editor/operations/sgroup/sgroupAttachmentPoints.js');
var index$3 = require('./application/editor/operations/sgroup/index.js');
var TextCreateDelete = require('./application/editor/operations/Text/TextCreateDelete.js');
var TextUpdate = require('./application/editor/operations/Text/TextUpdate.js');
var TextMove = require('./application/editor/operations/Text/TextMove.js');
var AttachmentPointHoverOperation = require('./application/editor/operations/monomer/AttachmentPointHoverOperation.js');
var FlipMonomerOperation = require('./application/editor/operations/monomer/FlipMonomerOperation.js');
var MonomerAddOperation = require('./application/editor/operations/monomer/MonomerAddOperation.js');
var MonomerDeleteOperation = require('./application/editor/operations/monomer/MonomerDeleteOperation.js');
var monomerFactory = require('./application/render/renderers/monomerFactory.js');
var MonomerHoverOperation = require('./application/editor/operations/monomer/MonomerHoverOperation.js');
var MonomerItemModifyOperation = require('./application/editor/operations/monomer/MonomerItemModifyOperation.js');
var MonomerMoveOperation = require('./application/editor/operations/monomer/MonomerMoveOperation.js');
var RotateMonomerOperation = require('./application/editor/operations/monomer/RotateMonomerOperation.js');
var ShiftMonomerOperation = require('./application/editor/operations/monomer/ShiftMonomerOperation.js');
var index$4 = require('./application/editor/operations/modes/index.js');
var AssignAttachmentAtomOperation = require('./application/editor/operations/monomerCreation/AssignAttachmentAtomOperation.js');
var AssignLeavingGroupAtomOperation = require('./application/editor/operations/monomerCreation/AssignLeavingGroupAtomOperation.js');
var MarkAsRnaComponentOperation = require('./application/editor/operations/monomerCreation/MarkAsRnaComponentOperation.js');
var ReassignAttachmentPointOperation = require('./application/editor/operations/monomerCreation/ReassignAttachmentPointOperation.js');
var ReassignLeavingAtomOperation = require('./application/editor/operations/monomerCreation/ReassignLeavingAtomOperation.js');
var action = require('./application/editor/actions/action.js');
var aromaticFusing = require('./application/editor/actions/aromaticFusing.js');
var bondStereo = require('./application/editor/actions/bondStereo.js');
var atom$1 = require('./application/editor/actions/atom.js');
var atomMerge = require('./application/editor/actions/atomMerge.js');
var basic = require('./application/editor/actions/basic.js');
var bond$1 = require('./application/editor/actions/bond.js');
var chain = require('./application/editor/actions/chain.js');
var closelyFusing = require('./application/editor/actions/closelyFusing.js');
var erase = require('./application/editor/actions/erase.js');
var fragment$1 = require('./application/editor/actions/fragment.js');
var paste = require('./application/editor/actions/paste.js');
var image$2 = require('./application/editor/actions/image.js');
var multitailArrow$2 = require('./application/editor/actions/multitailArrow.js');
var reaction = require('./application/editor/actions/reaction.js');
var rgroup$1 = require('./application/editor/actions/rgroup.js');
var rgroupAttachmentPoint$1 = require('./application/editor/actions/rgroupAttachmentPoint.js');
var rotate = require('./application/editor/actions/rotate.js');
var sgroup$1 = require('./application/editor/actions/sgroup.js');
var simpleobject = require('./application/editor/actions/simpleobject.js');
var template = require('./application/editor/actions/template.js');
var text$1 = require('./application/editor/actions/text.js');
var utils$1 = require('./application/editor/actions/utils.js');
var highlight$1 = require('./application/editor/actions/highlight.js');
var constants$1 = require('./application/editor/shared/constants.js');
var coordinates = require('./application/editor/shared/coordinates.js');
var customEvents = require('./application/editor/shared/customEvents.js');
var editor_types = require('./application/editor/editor.types.js');
var Editor = require('./application/editor/Editor.js');
var editorSingleton = require('./application/editor/editorSingleton.js');
var sort = require('./application/editor/shared/sort.js');
var EditorHistory = require('./application/editor/EditorHistory.js');
var FlexMode = require('./application/editor/modes/FlexMode.js');
var SequenceMode = require('./application/editor/modes/SequenceMode.js');
var SnakeMode = require('./application/editor/modes/SnakeMode.js');
var index$5 = require('./application/editor/modes/types/index.js');
var helpers$2 = require('./application/editor/modes/helpers.js');
var editorEvents = require('./application/editor/editorEvents.js');
var editorSettings = require('./application/editor/editorSettings.js');
var Tool = require('./application/editor/tools/Tool.js');
var Zoom = require('./application/editor/tools/Zoom.js');
var SelectBase = require('./application/editor/tools/select/SelectBase.js');
var SelectRectangle = require('./application/editor/tools/select/SelectRectangle.js');
var SelectLasso = require('./application/editor/tools/select/SelectLasso.js');
var SelectFragment = require('./application/editor/tools/select/SelectFragment.js');
var rnaPresetConnections = require('./application/editor/tools/rnaPresetConnections.js');
var index$6 = require('./application/editor/tools/index.js');
var MacromoleculesConverter = require('./application/editor/MacromoleculesConverter.js');
var types$1 = require('./application/editor/tools/types.js');
var monomerItem = require('./domain/helpers/monomerItem.js');



exports.ElementColor = elementColor.ElementColor;
exports.Elements = elements.Elements;
Object.defineProperty(exports, 'AtomLabel', {
	enumerable: true,
	get: function () { return element_types.AtomLabel; }
});
exports.Generics = generics.Generics;
exports.genericsList = generics.genericsList;
exports.IMAGE_KEY = image.IMAGE_KEY;
exports.IMAGE_SERIALIZE_KEY = image.IMAGE_SERIALIZE_KEY;
exports.imageReferencePositionToCursor = image.imageReferencePositionToCursor;
exports.MULTITAIL_ARROW_KEY = multitailArrow.MULTITAIL_ARROW_KEY;
exports.MULTITAIL_ARROW_SERIALIZE_KEY = multitailArrow.MULTITAIL_ARROW_SERIALIZE_KEY;
exports.MULTITAIL_ARROW_TOOL_NAME = multitailArrow.MULTITAIL_ARROW_TOOL_NAME;
exports.multitailArrowReferenceLinesToCursor = multitailArrow.multitailArrowReferenceLinesToCursor;
exports.multitailReferencePositionToCursor = multitailArrow.multitailReferencePositionToCursor;
Object.defineProperty(exports, 'STRAND_TYPE', {
	enumerable: true,
	get: function () { return chains.STRAND_TYPE; }
});
exports.CREATE_MONOMER_TOOL_NAME = monomers.CREATE_MONOMER_TOOL_NAME;
exports.HalfMonomerSize = monomers.HalfMonomerSize;
Object.defineProperty(exports, 'KetMonomerClass', {
	enumerable: true,
	get: function () { return monomers.KetMonomerClass; }
});
exports.MONOMER_CONST = monomers.MONOMER_CONST;
exports.MonomerSize = monomers.MonomerSize;
exports.NO_NATURAL_ANALOGUE = monomers.NO_NATURAL_ANALOGUE;
Object.defineProperty(exports, 'RNA_DNA_NON_MODIFIED_PART', {
	enumerable: true,
	get: function () { return monomers.RNA_DNA_NON_MODIFIED_PART; }
});
Object.defineProperty(exports, 'RnaDnaBaseNames', {
	enumerable: true,
	get: function () { return monomers.RnaDnaBaseNames; }
});
Object.defineProperty(exports, 'RnaDnaNaturalAnaloguesEnum', {
	enumerable: true,
	get: function () { return monomers.RnaDnaNaturalAnaloguesEnum; }
});
Object.defineProperty(exports, 'StandardAmbiguousPeptide', {
	enumerable: true,
	get: function () { return monomers.StandardAmbiguousPeptide; }
});
Object.defineProperty(exports, 'StandardAmbiguousRnaBase', {
	enumerable: true,
	get: function () { return monomers.StandardAmbiguousRnaBase; }
});
exports.StandardBondLength = monomers.StandardBondLength;
exports.peptideAmbiguousSymbols = monomers.peptideAmbiguousSymbols;
exports.peptideNaturalAnalogues = monomers.peptideNaturalAnalogues;
exports.rnaDnaAmbiguousSymbols = monomers.rnaDnaAmbiguousSymbols;
exports.rnaDnaNaturalAnalogues = monomers.rnaDnaNaturalAnalogues;
exports.unknownNaturalAnalogues = monomers.unknownNaturalAnalogues;
exports.SnakeLayoutCellWidth = layout.SnakeLayoutCellWidth;
exports.Atom = atom.Atom;
Object.defineProperty(exports, 'AttachmentPoints', {
	enumerable: true,
	get: function () { return atom.AttachmentPoints; }
});
Object.defineProperty(exports, 'StereoLabel', {
	enumerable: true,
	get: function () { return atom.StereoLabel; }
});
exports.radicalElectrons = atom.radicalElectrons;
exports.AtomList = atomList.AtomList;
exports.Bond = bond.Bond;
exports.FixedPrecisionCoordinates = fixedPrecision.FixedPrecisionCoordinates;
exports.Fragment = fragment.Fragment;
Object.defineProperty(exports, 'StereoFlag', {
	enumerable: true,
	get: function () { return fragment.StereoFlag; }
});
exports.FunctionalGroup = functionalGroup.FunctionalGroup;
exports.HalfBond = halfBond.HalfBond;
exports.Loop = loop.Loop;
exports.RGroup = rgroup.RGroup;
exports.RGroupAttachmentPoint = rgroupAttachmentPoint.RGroupAttachmentPoint;
exports.RxnArrow = rxnArrow.RxnArrow;
Object.defineProperty(exports, 'RxnArrowMode', {
	enumerable: true,
	get: function () { return rxnArrow.RxnArrowMode; }
});
exports.RxnPlus = rxnPlus.RxnPlus;
exports.SGroup = sgroup.SGroup;
exports.SGroupBracketParams = sgroup.SGroupBracketParams;
Object.defineProperty(exports, 'SUPERATOM_CLASS', {
	enumerable: true,
	get: function () { return sgroup.SUPERATOM_CLASS; }
});
exports.SGroupForest = sgroupForest.SGroupForest;
exports.checkOverlapping = sgroupForest.checkOverlapping;
exports.SimpleObject = simpleObject.SimpleObject;
Object.defineProperty(exports, 'SimpleObjectMode', {
	enumerable: true,
	get: function () { return simpleObject.SimpleObjectMode; }
});
exports.Struct = struct.Struct;
exports.Text = text.Text;
Object.defineProperty(exports, 'TextCommand', {
	enumerable: true,
	get: function () { return text.TextCommand; }
});
exports.Pile = pile.Pile;
exports.Vec2 = vec2.Vec2;
exports.Box2Abs = box2Abs.Box2Abs;
exports.Pool = pool.Pool;
exports.Image = image$1.Image;
exports.MultitailArrow = multitailArrow$1.MultitailArrow;
exports.Highlight = highlight.Highlight;
exports.SGroupAttachmentPoint = sGroupAttachmentPoint.SGroupAttachmentPoint;
exports.MonomerMicromolecule = monomerMicromolecule.MonomerMicromolecule;
exports.Peptide = Peptide.Peptide;
exports.BaseMonomer = BaseMonomer.BaseMonomer;
exports.HYDROGEN_BOND_ATTACHMENT_POINT = BaseMonomer.HYDROGEN_BOND_ATTACHMENT_POINT;
exports.Chem = Chem.Chem;
exports.Sugar = Sugar.Sugar;
exports.RNABase = RNABase.RNABase;
exports.Phosphate = Phosphate.Phosphate;
Object.defineProperty(exports, 'Axis', {
	enumerable: true,
	get: function () { return Axis.Axis; }
});
exports.Nucleoside = Nucleoside.Nucleoside;
exports.Nucleotide = Nucleotide.Nucleotide;
Object.defineProperty(exports, 'IsChainCycled', {
	enumerable: true,
	get: function () { return types.IsChainCycled; }
});
Object.defineProperty(exports, 'SequenceType', {
	enumerable: true,
	get: function () { return types.SequenceType; }
});
exports.Chain = Chain.Chain;
exports.ChainsCollection = ChainsCollection.ChainsCollection;
exports.MonomerSequenceNode = MonomerSequenceNode.MonomerSequenceNode;
exports.EmptySequenceNode = EmptySequenceNode.EmptySequenceNode;
exports.LinkerSequenceNode = LinkerSequenceNode.LinkerSequenceNode;
exports.UnresolvedMonomer = UnresolvedMonomer.UnresolvedMonomer;
exports.UnsplitNucleotide = UnsplitNucleotide.UnsplitNucleotide;
exports.PolymerBond = PolymerBond.PolymerBond;
exports.AmbiguousMonomer = AmbiguousMonomer.AmbiguousMonomer;
exports.DEFAULT_VARIANT_MONOMER_LABEL = AmbiguousMonomer.DEFAULT_VARIANT_MONOMER_LABEL;
exports.MONOMER_CLASS_TO_CONSTRUCTOR = AmbiguousMonomer.MONOMER_CLASS_TO_CONSTRUCTOR;
exports.MonomerToAtomBond = MonomerToAtomBond.MonomerToAtomBond;
exports.HydrogenBond = HydrogenBond.HydrogenBond;
exports.SGroupDrawingEntity = SGroupDrawingEntity.SGroupDrawingEntity;
exports.BackBoneSequenceNode = BackBoneSequenceNode.BackBoneSequenceNode;
exports.replaceMonomer = DrawingEntitiesManager_replaceMonomer.replaceMonomer;
exports.Command = Command.Command;
exports.CoreAtom = CoreAtom.Atom;
exports.CoreStereoFlag = CoreStereoFlag.CoreStereoFlag;
exports.KetSerializer = ketSerializer.KetSerializer;
exports.fillNaturalAnalogueForPhosphateAndSugar = helpers.fillNaturalAnalogueForPhosphateAndSugar;
exports.getHELMClassByKetMonomerClass = helpers.getHELMClassByKetMonomerClass;
exports.getKetRef = helpers.getKetRef;
exports.getMonomerTemplateRefFromMonomerItem = helpers.getMonomerTemplateRefFromMonomerItem;
exports.getNodeWithInvertedYCoord = helpers.getNodeWithInvertedYCoord;
exports.modifyTransformation = helpers.modifyTransformation;
exports.populateStructWithSelection = helpers.populateStructWithSelection;
exports.setAmbiguousMonomerPrefix = helpers.setAmbiguousMonomerPrefix;
exports.setAmbiguousMonomerTemplatePrefix = helpers.setAmbiguousMonomerTemplatePrefix;
exports.setMonomerGroupTemplatePrefix = helpers.setMonomerGroupTemplatePrefix;
exports.setMonomerPrefix = helpers.setMonomerPrefix;
exports.setMonomerTemplatePrefix = helpers.setMonomerTemplatePrefix;
exports.switchIntoChemistryCoordSystem = helpers.switchIntoChemistryCoordSystem;
exports.MolSerializer = molSerializer.MolSerializer;
exports.SdfSerializer = sdfSerializer.SdfSerializer;
Object.defineProperty(exports, 'ChemicalMimeType', {
	enumerable: true,
	get: function () { return structService_types.ChemicalMimeType; }
});
exports.Scale = scale.Scale;
exports.StereoValidator = stereoValidator.StereoValidator;
exports.FunctionalGroupsProvider = functionalGroupsProvider.FunctionalGroupsProvider;
exports.SaltsAndSolventsProvider = saltsAndSolventsProvider.SaltsAndSolventsProvider;
exports.getAttachmentPointLabel = attachmentPointCalculations.getAttachmentPointLabel;
exports.getAttachmentPointLabelWithBinaryShift = attachmentPointCalculations.getAttachmentPointLabelWithBinaryShift;
exports.getAttachmentPointNumberFromLabel = attachmentPointCalculations.getAttachmentPointNumberFromLabel;
exports.getNextFreeAttachmentPoint = attachmentPointCalculations.getNextFreeAttachmentPoint;
exports.isSingleRGroupAttachmentPoint = attachmentPointCalculations.isSingleRGroupAttachmentPoint;
Object.defineProperty(exports, 'AttachmentPointName', {
	enumerable: true,
	get: function () { return monomers$1.AttachmentPointName; }
});
exports.attachmentPointNames = monomers$1.attachmentPointNames;
Object.defineProperty(exports, 'Entities', {
	enumerable: true,
	get: function () { return entities.Entities; }
});
exports.RemoteStructService = remoteStructService.RemoteStructService;
exports.pickStandardServerOptions = remoteStructService.pickStandardServerOptions;
exports.RemoteStructServiceProvider = remoteStructServiceProvider.RemoteStructServiceProvider;
exports.getLabelRenderModeForIndigo = helpers$1.getLabelRenderModeForIndigo;
exports.SupportedFormatProperties = supportedFormatProperties.SupportedFormatProperties;
exports.formatProperties = formatProperties.formatProperties;
exports.getFormatMimeTypeByFileName = formatProperties.getFormatMimeTypeByFileName;
exports.getPropertiesByFormat = formatProperties.getPropertiesByFormat;
exports.getPropertiesByImgFormat = formatProperties.getPropertiesByImgFormat;
Object.defineProperty(exports, 'SupportedFormat', {
	enumerable: true,
	get: function () { return structFormatter_types.SupportedFormat; }
});
exports.FormatterFactory = formatterFactory.FormatterFactory;
exports.identifyStructFormat = identifyStructFormat.identifyStructFormat;
exports.macromoleculesFilesInputFormats = constants.macromoleculesFilesInputFormats;
Object.defineProperty(exports, 'KetAmbiguousMonomerTemplateSubType', {
	enumerable: true,
	get: function () { return ket.KetAmbiguousMonomerTemplateSubType; }
});
Object.defineProperty(exports, 'KetConnectionType', {
	enumerable: true,
	get: function () { return ket.KetConnectionType; }
});
Object.defineProperty(exports, 'KetMonomerGroupTemplateClass', {
	enumerable: true,
	get: function () { return ket.KetMonomerGroupTemplateClass; }
});
Object.defineProperty(exports, 'KetNodeType', {
	enumerable: true,
	get: function () { return ket.KetNodeType; }
});
Object.defineProperty(exports, 'KetTemplateType', {
	enumerable: true,
	get: function () { return ket.KetTemplateType; }
});
exports.RenderStruct = renderStruct.RenderStruct;
exports.Render = raphaelRender.Render;
exports.ReObject = reobject["default"];
exports.ReAtom = reatom["default"];
Object.defineProperty(exports, 'ShowHydrogenLabelNames', {
	enumerable: true,
	get: function () { return reatom.ShowHydrogenLabelNames; }
});
exports.checkIsSmartPropertiesExist = reatom.checkIsSmartPropertiesExist;
exports.getAtomCustomQuery = reatom.getAtomCustomQuery;
exports.getAtomType = reatom.getAtomType;
exports.getColorFromStereoLabel = reatom.getColorFromStereoLabel;
exports.ReBond = rebond["default"];
exports.ReEnhancedFlag = reenhancedFlag["default"];
exports.ReFrag = refrag["default"];
exports.ReRGroup = rergroup["default"];
exports.ReRxnArrow = rerxnarrow["default"];
exports.ReRxnPlus = rerxnplus["default"];
exports.ReSGroup = resgroup["default"];
exports.paperPathFromSVGElement = resgroup.paperPathFromSVGElement;
exports.ReSimpleObject = resimpleObject["default"];
exports.ReStruct = restruct["default"];
exports.ReText = retext["default"];
exports.Visel = visel["default"];
Object.defineProperty(exports, 'LayerMap', {
	enumerable: true,
	get: function () { return generalEnumTypes.LayerMap; }
});
Object.defineProperty(exports, 'StereoColoringType', {
	enumerable: true,
	get: function () { return generalEnumTypes.StereoColoringType; }
});
Object.defineProperty(exports, 'StereoLabelStyleType', {
	enumerable: true,
	get: function () { return generalEnumTypes.StereoLabelStyleType; }
});
Object.defineProperty(exports, 'ShowHydrogenLabels', {
	enumerable: true,
	get: function () { return showHydrogenLabels.ShowHydrogenLabels; }
});
exports.ReRGroupAttachmentPoint = rergroupAttachmentPoint.ReRGroupAttachmentPoint;
exports.ReImage = reImage.ReImage;
Object.defineProperty(exports, 'MultitailArrowRefName', {
	enumerable: true,
	get: function () { return remultitailArrow.MultitailArrowRefName; }
});
exports.ReMultitailArrow = remultitailArrow.ReMultitailArrow;
exports.convertDraftToLexical = draftToLexical.convertDraftToLexical;
exports.BaseRenderer = BaseRenderer.BaseRenderer;
exports.BaseMonomerRenderer = BaseMonomerRenderer.BaseMonomerRenderer;
exports.ChemRenderer = ChemRenderer.ChemRenderer;
exports.PeptideRenderer = PeptideRenderer.PeptideRenderer;
exports.PhosphateRenderer = PhosphateRenderer.PhosphateRenderer;
exports.SugarRenderer = SugarRenderer.SugarRenderer;
exports.RNABaseRenderer = RNABaseRenderer.RNABaseRenderer;
exports.UnresolvedMonomerRenderer = UnresolvedMonomerRenderer.UnresolvedMonomerRenderer;
exports.UnsplitNucleotideRenderer = UnsplitNucleotideRenderer.UnsplitNucleotideRenderer;
exports.AmbiguousMonomerRenderer = AmbiguousMonomerRenderer.AmbiguousMonomerRenderer;
exports.SGroupRenderer = SGroupRenderer.SGroupRenderer;
exports.RenderersManager = RenderersManager.RenderersManager;
exports.getRenderedStructuresBbox = utils.getRenderedStructuresBbox;
exports.StereoFlagRenderer = StereoFlagRenderer.StereoFlagRenderer;
exports.SequenceRenderer = SequenceRenderer.SequenceRenderer;
exports.BaseSequenceItemRenderer = BaseSequenceItemRenderer.BaseSequenceItemRenderer;
exports.BackBoneBondSequenceRenderer = BackBoneBondSequenceRenderer.BackBoneBondSequenceRenderer;
exports.BaseSequenceRenderer = BaseSequenceRenderer.BaseSequenceRenderer;
exports.ChemSequenceItemRenderer = ChemSequenceItemRenderer.ChemSequenceItemRenderer;
exports.EmptySequenceItemRenderer = EmptySequenceItemRenderer.EmptySequenceItemRenderer;
exports.NucleotideSequenceItemRenderer = NucleotideSequenceItemRenderer.NucleotideSequenceItemRenderer;
exports.NucleosideSequenceItemRenderer = NucleosideSequenceItemRenderer.NucleosideSequenceItemRenderer;
exports.PeptideSequenceItemRenderer = PeptideSequenceItemRenderer.PeptideSequenceItemRenderer;
exports.PhosphateSequenceItemRenderer = PhosphateSequenceItemRenderer.PhosphateSequenceItemRenderer;
exports.PolymerBondSequenceRenderer = PolymerBondSequenceRenderer.PolymerBondSequenceRenderer;
exports.RNASequenceItemRenderer = RNASequenceItemRenderer.RNASequenceItemRenderer;
exports.SequenceNodeRendererFactory = SequenceNodeRendererFactory.SequenceNodeRendererFactory;
exports.UnresolvedMonomerSequenceItemRenderer = UnresolvedMonomerSequenceItemRenderer.UnresolvedMonomerSequenceItemRenderer;
exports.UnsplitNucleotideSequenceItemRenderer = UnsplitNucleotideSequenceItemRenderer.UnsplitNucleotideSequenceItemRenderer;
exports.CoordinateTransformation = coordinateTransformation.CoordinateTransformation;
exports.ScrollbarContainer = scrollbarContainer.ScrollbarContainer;
exports.notifyItemsToMergeInitializationComplete = notifyRenderComplete.notifyItemsToMergeInitializationComplete;
exports.notifyRenderComplete = notifyRenderComplete.notifyRenderComplete;
exports.getOptionsWithConvertedUnits = options.getOptionsWithConvertedUnits;
Object.defineProperty(exports, 'MeasurementUnits', {
	enumerable: true,
	get: function () { return render_types.MeasurementUnits; }
});
exports.vectorUtils = index.vectorUtils;
exports.Ketcher = ketcher.Ketcher;
Object.defineProperty(exports, 'BlobTypes', {
	enumerable: true,
	get: function () { return ketcher_types.BlobTypes; }
});
Object.defineProperty(exports, 'ModeTypes', {
	enumerable: true,
	get: function () { return ketcher_types.ModeTypes; }
});
exports.DefaultStructServiceOptions = ketcherBuilder.DefaultStructServiceOptions;
exports.KetcherBuilder = ketcherBuilder.KetcherBuilder;
exports.SettingsValidationError = types$2.SettingsValidationError;
exports.SettingsService = SettingsService.SettingsService;
exports.LocalStorageAdapter = LocalStorageAdapter.LocalStorageAdapter;
exports.MemoryStorageAdapter = MemoryStorageAdapter.MemoryStorageAdapter;
exports.SchemaValidator = SchemaValidator.SchemaValidator;
exports.SettingsMigration = SettingsMigration.SettingsMigration;
exports.PRESETS = schema.PRESETS;
exports.SCHEMA = schema.SCHEMA;
exports.getDefaultSettings = schema.getDefaultSettings;
exports.normalizeSettingsForCore = settingsFormatters.normalizeSettingsForCore;
exports.normalizeSettingsForForm = settingsFormatters.normalizeSettingsForForm;
exports.deleteAllEntitiesOnCanvas = utils$2.deleteAllEntitiesOnCanvas;
exports.parseAndAddMacromoleculesOnCanvas = utils$2.parseAndAddMacromoleculesOnCanvas;
exports.parseStruct = utils$2.parseStruct;
exports.prepareStructToRender = utils$2.prepareStructToRender;
exports.ketcherProvider = ketcherProvider.ketcherProvider;
exports.getStructure = getStructure.getStructure;
exports.canModifyAminoAcid = monomers$2.canModifyAminoAcid;
exports.checkIsR2R1Connection = monomers$2.checkIsR2R1Connection;
exports.getAllConnectedMonomersRecursively = monomers$2.getAllConnectedMonomersRecursively;
exports.getAminoAcidsToModify = monomers$2.getAminoAcidsToModify;
exports.getMonomerUniqueKey = monomers$2.getMonomerUniqueKey;
exports.getNextMonomerInChain = monomers$2.getNextMonomerInChain;
exports.getPhosphateFromSugar = monomers$2.getPhosphateFromSugar;
exports.getPreviousMonomerInChain = monomers$2.getPreviousMonomerInChain;
exports.getRnaBaseFromSugar = monomers$2.getRnaBaseFromSugar;
exports.getSugarFromRnaBase = monomers$2.getSugarFromRnaBase;
exports.isAmbiguousMonomerLibraryItem = monomers$2.isAmbiguousMonomerLibraryItem;
exports.isBondBetweenSugarAndBaseOfRna = monomers$2.isBondBetweenSugarAndBaseOfRna;
exports.isHelmCompatible = monomers$2.isHelmCompatible;
exports.isLibraryItemRnaPreset = monomers$2.isLibraryItemRnaPreset;
exports.isMonomerBeginningOfChain = monomers$2.isMonomerBeginningOfChain;
exports.isMonomerConnectedToR2RnaBase = monomers$2.isMonomerConnectedToR2RnaBase;
exports.isPeptideOrAmbiguousPeptide = monomers$2.isPeptideOrAmbiguousPeptide;
exports.isPhosphateOrAmbiguousPhosphate = monomers$2.isPhosphateOrAmbiguousPhosphate;
exports.isR2R1ConnectionFromRnaBase = monomers$2.isR2R1ConnectionFromRnaBase;
exports.isRnaBaseApplicableForAntisense = monomers$2.isRnaBaseApplicableForAntisense;
exports.isRnaBaseOrAmbiguousRnaBase = monomers$2.isRnaBaseOrAmbiguousRnaBase;
exports.isRnaBaseVariantMonomer = monomers$2.isRnaBaseVariantMonomer;
exports.isSugarOrAmbiguousSugar = monomers$2.isSugarOrAmbiguousSugar;
exports.isValidNucleoside = monomers$2.isValidNucleoside;
exports.isValidNucleotide = monomers$2.isValidNucleotide;
exports.libraryItemHasR1AttachmentPoint = monomers$2.libraryItemHasR1AttachmentPoint;
exports.normalizeMonomerAtomsPositions = monomers$2.normalizeMonomerAtomsPositions;
exports.ifDef = ifDef.ifDef;
exports.toFixed = toFixed.toFixed;
Object.defineProperty(exports, 'KetcherAsyncEvents', {
	enumerable: true,
	get: function () { return runAsyncAction.KetcherAsyncEvents; }
});
exports.runAsyncAction = runAsyncAction.runAsyncAction;
exports.b64toBlob = b64toBlob.b64toBlob;
exports.notifyRequestCompleted = notifyRequestCompleted.notifyRequestCompleted;
exports.KetcherLogger = KetcherLogger.KetcherLogger;
Object.defineProperty(exports, 'LogLevel', {
	enumerable: true,
	get: function () { return KetcherLogger.LogLevel; }
});
exports.KETCHER_SAVED_OPTIONS_KEY = SettingsManager.KETCHER_SAVED_OPTIONS_KEY;
exports.KETCHER_SAVED_SETTINGS_KEY = SettingsManager.KETCHER_SAVED_SETTINGS_KEY;
exports.SetEditorLineLengthAction = SettingsManager.SetEditorLineLengthAction;
exports.SettingsManager = SettingsManager.SettingsManager;
exports.CanonicalModifiersOrder = keynorm.CanonicalModifiersOrder;
exports.KeyCodePrefixes = keynorm.KeyCodePrefixes;
exports.KeyboardModifiers = keynorm.KeyboardModifiers;
exports.ModifiersRegex = keynorm.ModifiersRegex;
exports.initHotKeys = keynorm.initHotKeys;
exports.isControlKey = keynorm.isControlKey;
exports.keyNorm = keynorm.keyNorm;
exports.generateMenuShortcuts = shortcutsUtil.generateMenuShortcuts;
exports.shortcutStr = shortcutsUtil.shortcutStr;
exports.getStructStringFromClipboardData = clipboardUtils.getStructStringFromClipboardData;
exports.isClipboardAPIAvailable = clipboardUtils.isClipboardAPIAvailable;
exports.legacyCopy = clipboardUtils.legacyCopy;
exports.legacyPaste = clipboardUtils.legacyPaste;
exports.notifyCopyCut = clipboardUtils.notifyCopyCut;
exports.safelyGetMimeType = clipboardUtils.safelyGetMimeType;
exports.getSvgFromDrawnStructures = getSvgFromDrawnStructures.getSvgFromDrawnStructures;
exports.ensureString = ensureString.ensureString;
exports.normalizeError = normalizeError.normalizeError;
exports.BILN_ALIAS_FORMAT_ERROR_MESSAGE = monomers$3.BILN_ALIAS_FORMAT_ERROR_MESSAGE;
exports.DISALLOWED_MODIFICATION_TYPE_ERROR_MESSAGE = monomers$3.DISALLOWED_MODIFICATION_TYPE_ERROR_MESSAGE;
exports.DISALLOWED_MONOMER_MODIFICATION_TYPES = monomers$3.DISALLOWED_MONOMER_MODIFICATION_TYPES;
exports.HELM_ALIAS_FORMAT_ERROR_MESSAGE = monomers$3.HELM_ALIAS_FORMAT_ERROR_MESSAGE;
exports.HELM_ALIAS_LENGTH_ERROR_MESSAGE = monomers$3.HELM_ALIAS_LENGTH_ERROR_MESSAGE;
exports.HELM_ALIAS_MAX_LENGTH = monomers$3.HELM_ALIAS_MAX_LENGTH;
exports.IDT_ALIAS_LENGTH_ERROR_MESSAGE = monomers$3.IDT_ALIAS_LENGTH_ERROR_MESSAGE;
exports.IDT_ALIAS_LENGTH_MAX = monomers$3.IDT_ALIAS_LENGTH_MAX;
exports.IDT_ALIAS_SLASH_ERROR_MESSAGE = monomers$3.IDT_ALIAS_SLASH_ERROR_MESSAGE;
exports.MONOMER_GROUP_TEMPLATE_NAME_MAX_LENGTH = monomers$3.MONOMER_GROUP_TEMPLATE_NAME_MAX_LENGTH;
exports.MONOMER_GROUP_TEMPLATE_NAME_MAX_LENGTH_ERROR_MESSAGE = monomers$3.MONOMER_GROUP_TEMPLATE_NAME_MAX_LENGTH_ERROR_MESSAGE;
exports.getDisallowedModificationTypes = monomers$3.getDisallowedModificationTypes;
exports.getTooLongIdtAliasEntries = monomers$3.getTooLongIdtAliasEntries;
exports.isMonomerSgroupWithAttachmentPoints = monomers$3.isMonomerSgroupWithAttachmentPoints;
exports.isValidBilnAlias = monomers$3.isValidBilnAlias;
exports.isValidHelmAlias = monomers$3.isValidHelmAlias;
exports.isValidHelmAliasLength = monomers$3.isValidHelmAliasLength;
exports.isValidIdtAlias = monomers$3.isValidIdtAlias;
exports.isValidIdtAliasLength = monomers$3.isValidIdtAliasLength;
exports.blurActiveElement = dom.blurActiveElement;
exports.isEditableInputTarget = dom.isEditableInputTarget;
Object.defineProperty(exports, 'UsageInMacromolecule', {
	enumerable: true,
	get: function () { return render_constants.UsageInMacromolecule; }
});
exports.AtomAttr = AtomAttr.AtomAttr;
exports.AtomMove = AtomMove.AtomMove;
exports.AtomAdd = AtomAdd.AtomAdd;
exports.AtomDelete = AtomDelete.AtomDelete;
exports.BondAttr = BondAttr.BondAttr;
exports.BondMove = BondMove.BondMove;
exports.BondAdd = BondAdd.BondAdd;
exports.BondDelete = BondDelete.BondDelete;
exports.CanvasLoad = CanvasLoad.CanvasLoad;
exports.AlignDescriptors = AlignDescriptors.AlignDescriptors;
exports.RestoreDescriptorsPosition = RestoreDescriptorsPosition.RestoreDescriptorsPosition;
exports.EnhancedFlagMove = EnhancedFlagMove.EnhancedFlagMove;
exports.EnhancedFlagClear = EnhancedFlagClear.EnhancedFlagClear;
exports.UpdateIfThen = UpdateIfThen.UpdateIfThen;
exports.RestoreIfThen = RestoreIfThen.RestoreIfThen;
exports.FragmentAdd = FragmentAdd.FragmentAdd;
exports.FragmentDelete = FragmentDelete.FragmentDelete;
exports.FragmentSetProperties = FragmentSetProperties.FragmentSetProperties;
exports.FragmentAddStereoAtom = FragmentAddStereoAtom.FragmentAddStereoAtom;
exports.FragmentDeleteStereoAtom = FragmentDeleteStereoAtom.FragmentDeleteStereoAtom;
exports.FragmentStereoFlag = FragmentStereoFlag.FragmentStereoFlag;
exports.CalcImplicitH = calcimplicitH.CalcImplicitH;
exports.LoopMove = LoopMove.LoopMove;
Object.defineProperty(exports, 'OperationPriority', {
	enumerable: true,
	get: function () { return OperationType.OperationPriority; }
});
exports.OperationType = OperationType.OperationType;
exports.ImageMove = imageMove.ImageMove;
exports.ImageResize = imageResize.ImageResize;
exports.ImageDelete = imageUpsertDelete.ImageDelete;
exports.ImageUpsert = imageUpsertDelete.ImageUpsert;
exports.MultitailArrowAddTail = multitailArrowAddRemoveTail.MultitailArrowAddTail;
exports.MultitailArrowRemoveTail = multitailArrowAddRemoveTail.MultitailArrowRemoveTail;
exports.MultitailArrowMove = multitailArrowMove.MultitailArrowMove;
exports.MultitailArrowMoveHeadTail = multitailArrowMoveHeadTail.MultitailArrowMoveHeadTail;
exports.MultitailArrowResizeTailHead = multitailArrowResizeTailHead.MultitailArrowResizeTailHead;
exports.MultitailArrowDelete = multitailArrowUpsertDelete.MultitailArrowDelete;
exports.MultitailArrowUpsert = multitailArrowUpsertDelete.MultitailArrowUpsert;
exports.RGroupAttr = RGroupAttr.RGroupAttr;
exports.RGroupFragment = RGroupFragment.RGroupFragment;
exports.RGroupAttachmentPointAdd = RGroupAttachmentPointAdd.RGroupAttachmentPointAdd;
exports.RGroupAttachmentPointRemove = RGroupAttachmentPointRemove.RGroupAttachmentPointRemove;
exports.RxnArrowMove = RxnArrowMove.RxnArrowMove;
exports.RxnArrowRotate = RxnArrowRotate.RxnArrowRotate;
exports.ARROW_MAX_SNAPPING_ANGLE = RxnArrowResize.ARROW_MAX_SNAPPING_ANGLE;
exports.RxnArrowResize = RxnArrowResize.RxnArrowResize;
exports.getSnappedArrowVector = RxnArrowResize.getSnappedArrowVector;
exports.RxnPlusMove = RxnPlusMove.RxnPlusMove;
exports.RxnPlusAdd = index$2.RxnPlusAdd;
exports.RxnPlusDelete = index$2.RxnPlusDelete;
exports.RxnArrowAdd = index$1.RxnArrowAdd;
exports.RxnArrowDelete = index$1.RxnArrowDelete;
exports.SimpleObjectAdd = simpleObject$1.SimpleObjectAdd;
exports.SimpleObjectDelete = simpleObject$1.SimpleObjectDelete;
exports.SimpleObjectMove = simpleObject$1.SimpleObjectMove;
exports.SimpleObjectResize = simpleObject$1.SimpleObjectResize;
exports.makeCircleFromEllipse = simpleObject$1.makeCircleFromEllipse;
exports.SGroupAtomAdd = sgroupAtom.SGroupAtomAdd;
exports.SGroupAtomRemove = sgroupAtom.SGroupAtomRemove;
exports.SGroupAttr = SGroupAttr.SGroupAttr;
exports.SGroupDataMove = SGroupDataMove.SGroupDataMove;
exports.SGroupAddToHierarchy = sgroupHierarchy.SGroupAddToHierarchy;
exports.SGroupRemoveFromHierarchy = sgroupHierarchy.SGroupRemoveFromHierarchy;
exports.SGroupAttachmentPointAdd = sgroupAttachmentPoints.SGroupAttachmentPointAdd;
exports.SGroupAttachmentPointRemove = sgroupAttachmentPoints.SGroupAttachmentPointRemove;
exports.SGroupCreate = index$3.SGroupCreate;
exports.SGroupDelete = index$3.SGroupDelete;
exports.TextCreate = TextCreateDelete.TextCreate;
exports.TextDelete = TextCreateDelete.TextDelete;
exports.TextUpdate = TextUpdate.TextUpdate;
exports.TextMove = TextMove.TextMove;
exports.AttachmentPointHoverOperation = AttachmentPointHoverOperation.AttachmentPointHoverOperation;
exports.FlipMonomerOperation = FlipMonomerOperation.FlipMonomerOperation;
exports.MonomerAddOperation = MonomerAddOperation.MonomerAddOperation;
exports.MonomerDeleteOperation = MonomerDeleteOperation.MonomerDeleteOperation;
exports.monomerFactory = monomerFactory.monomerFactory;
exports.MonomerHoverOperation = MonomerHoverOperation.MonomerHoverOperation;
exports.MonomerItemModifyOperation = MonomerItemModifyOperation.MonomerItemModifyOperation;
exports.MonomerMoveOperation = MonomerMoveOperation.MonomerMoveOperation;
exports.RotateMonomerOperation = RotateMonomerOperation.RotateMonomerOperation;
exports.ShiftMonomerOperation = ShiftMonomerOperation.ShiftMonomerOperation;
exports.ReinitializeModeOperation = index$4.ReinitializeModeOperation;
exports.RestoreSequenceCaretPositionOperation = index$4.RestoreSequenceCaretPositionOperation;
exports.AssignAttachmentAtomOperation = AssignAttachmentAtomOperation.AssignAttachmentAtomOperation;
exports.AssignLeavingGroupAtomOperation = AssignLeavingGroupAtomOperation.AssignLeavingGroupAtomOperation;
exports.RemoveAttachmentPointOperation = AssignLeavingGroupAtomOperation.RemoveAttachmentPointOperation;
exports.MarkAsRnaComponentOperation = MarkAsRnaComponentOperation.MarkAsRnaComponentOperation;
exports.ReassignAttachmentPointOperation = ReassignAttachmentPointOperation.ReassignAttachmentPointOperation;
exports.ReassignLeavingAtomOperation = ReassignLeavingAtomOperation.ReassignLeavingAtomOperation;
exports.Action = action.Action;
exports.fromAromaticTemplateOnBond = aromaticFusing.fromAromaticTemplateOnBond;
exports.fromBondStereoUpdate = bondStereo.fromBondStereoUpdate;
exports.fromStereoAtomAttrs = bondStereo.fromStereoAtomAttrs;
exports.checkAtomValence = atom$1.checkAtomValence;
exports.fromAtomAddition = atom$1.fromAtomAddition;
exports.fromAtomsAttrs = atom$1.fromAtomsAttrs;
exports.fromAtomsFragmentAttr = atom$1.fromAtomsFragmentAttr;
exports.mergeFragmentsIfNeeded = atom$1.mergeFragmentsIfNeeded;
exports.mergeSgroups = atom$1.mergeSgroups;
exports.fromAtomMerge = atomMerge.fromAtomMerge;
exports.fromDescriptorsAlign = basic.fromDescriptorsAlign;
exports.fromNewCanvas = basic.fromNewCanvas;
exports.bondChangingAction = bond$1.bondChangingAction;
exports.fromBondAddition = bond$1.fromBondAddition;
exports.fromBondFlipping = bond$1.fromBondFlipping;
exports.fromBondsAttrs = bond$1.fromBondsAttrs;
exports.fromBondsMerge = bond$1.fromBondsMerge;
exports.removeAttachmentPointFromSuperatom = bond$1.removeAttachmentPointFromSuperatom;
exports.fromChain = chain.fromChain;
exports.removeInfoLabelFromAtoms = chain.removeInfoLabelFromAtoms;
exports.fromItemsFuse = closelyFusing.fromItemsFuse;
exports.getHoverToFuse = closelyFusing.getHoverToFuse;
exports.getItemsToFuse = closelyFusing.getItemsToFuse;
exports.mergeMapOfItemsToSet = closelyFusing.mergeMapOfItemsToSet;
exports.fromFragmentDeletion = erase.fromFragmentDeletion;
exports.fromOneAtomDeletion = erase.fromOneAtomDeletion;
exports.fromOneBondDeletion = erase.fromOneBondDeletion;
exports.fromFragmentSplit = fragment$1.fromFragmentSplit;
exports.fromMultipleMove = fragment$1.fromMultipleMove;
exports.fromStereoFlagUpdate = fragment$1.fromStereoFlagUpdate;
exports.fromPaste = paste.fromPaste;
exports.fromImageCreation = image$2.fromImageCreation;
exports.fromImageDeletion = image$2.fromImageDeletion;
exports.fromImageMove = image$2.fromImageMove;
exports.fromImageResize = image$2.fromImageResize;
exports.fromMultitailArrowCreation = multitailArrow$2.fromMultitailArrowCreation;
exports.fromMultitailArrowDeletion = multitailArrow$2.fromMultitailArrowDeletion;
exports.fromMultitailArrowHeadTailMove = multitailArrow$2.fromMultitailArrowHeadTailMove;
exports.fromMultitailArrowHeadTailsResize = multitailArrow$2.fromMultitailArrowHeadTailsResize;
exports.fromMultitailArrowMove = multitailArrow$2.fromMultitailArrowMove;
exports.fromMultitailArrowTailAdd = multitailArrow$2.fromMultitailArrowTailAdd;
exports.fromMultitailArrowTailRemove = multitailArrow$2.fromMultitailArrowTailRemove;
exports.fromArrowAddition = reaction.fromArrowAddition;
exports.fromArrowDeletion = reaction.fromArrowDeletion;
exports.fromArrowResizing = reaction.fromArrowResizing;
exports.fromPlusAddition = reaction.fromPlusAddition;
exports.fromPlusDeletion = reaction.fromPlusDeletion;
exports.fromRGroupAttrs = rgroup$1.fromRGroupAttrs;
exports.fromRGroupFragment = rgroup$1.fromRGroupFragment;
exports.fromUpdateIfThen = rgroup$1.fromUpdateIfThen;
exports.fromRGroupAttachmentPointAddition = rgroupAttachmentPoint$1.fromRGroupAttachmentPointAddition;
exports.fromRGroupAttachmentPointDeletion = rgroupAttachmentPoint$1.fromRGroupAttachmentPointDeletion;
exports.fromRGroupAttachmentPointUpdate = rgroupAttachmentPoint$1.fromRGroupAttachmentPointUpdate;
exports.flipBonds = rotate.flipBonds;
exports.fromFlip = rotate.fromFlip;
exports.fromRotate = rotate.fromRotate;
exports.expandSGroupWithMultipleAttachmentPoint = sgroup$1.expandSGroupWithMultipleAttachmentPoint;
exports.fromSeveralSgroupAddition = sgroup$1.fromSeveralSgroupAddition;
exports.fromSgroupAction = sgroup$1.fromSgroupAction;
exports.fromSgroupAddition = sgroup$1.fromSgroupAddition;
exports.fromSgroupAttachmentPointAddition = sgroup$1.fromSgroupAttachmentPointAddition;
exports.fromSgroupAttachmentPointRemove = sgroup$1.fromSgroupAttachmentPointRemove;
exports.fromSgroupAttrs = sgroup$1.fromSgroupAttrs;
exports.fromSgroupDeletion = sgroup$1.fromSgroupDeletion;
exports.removeAtomFromSgroupIfNeeded = sgroup$1.removeAtomFromSgroupIfNeeded;
exports.removeSgroupIfNeeded = sgroup$1.removeSgroupIfNeeded;
exports.sGroupAttributeAction = sgroup$1.sGroupAttributeAction;
exports.setExpandMonomerSGroup = sgroup$1.setExpandMonomerSGroup;
exports.setExpandSGroup = sgroup$1.setExpandSGroup;
exports.fromSimpleObjectAddition = simpleobject.fromSimpleObjectAddition;
exports.fromSimpleObjectDeletion = simpleobject.fromSimpleObjectDeletion;
exports.fromSimpleObjectResizing = simpleobject.fromSimpleObjectResizing;
exports.fromTemplateOnAtom = template.fromTemplateOnAtom;
exports.fromTemplateOnBondAction = template.fromTemplateOnBondAction;
exports.fromTemplateOnCanvas = template.fromTemplateOnCanvas;
exports.fromTextCreation = text$1.fromTextCreation;
exports.fromTextDeletion = text$1.fromTextDeletion;
exports.fromTextUpdating = text$1.fromTextUpdating;
exports.atomForNewBond = utils$1.atomForNewBond;
exports.atomGetAttr = utils$1.atomGetAttr;
exports.atomGetDegree = utils$1.atomGetDegree;
exports.atomGetPos = utils$1.atomGetPos;
exports.atomGetSGroups = utils$1.atomGetSGroups;
exports.findStereoAtoms = utils$1.findStereoAtoms;
exports.formatSelection = utils$1.formatSelection;
exports.getRelSGroupsBySelection = utils$1.getRelSGroupsBySelection;
exports.getSelectionFromStruct = utils$1.getSelectionFromStruct;
exports.isAttachmentBond = utils$1.isAttachmentBond;
exports.structSelection = utils$1.structSelection;
exports.fromHighlightClear = highlight$1.fromHighlightClear;
exports.fromHighlightCreate = highlight$1.fromHighlightCreate;
exports.MonomerCodeToGroup = constants$1.MonomerCodeToGroup;
Object.defineProperty(exports, 'MonomerGroupCodes', {
	enumerable: true,
	get: function () { return constants$1.MonomerGroupCodes; }
});
Object.defineProperty(exports, 'MonomerGroups', {
	enumerable: true,
	get: function () { return constants$1.MonomerGroups; }
});
exports.SgContexts = constants$1.SgContexts;
exports.defaultBondThickness = constants$1.defaultBondThickness;
exports.selectionKeys = constants$1.selectionKeys;
exports.Coordinates = coordinates.Coordinates;
exports.MonomerCreationAttachmentPointClickEvent = customEvents.MonomerCreationAttachmentPointClickEvent;
exports.MonomerCreationComponentStructureUpdateEvent = customEvents.MonomerCreationComponentStructureUpdateEvent;
Object.defineProperty(exports, 'EditorType', {
	enumerable: true,
	get: function () { return editor_types.EditorType; }
});
exports.CoreEditor = Editor.CoreEditor;
exports.EditorClassName = Editor.EditorClassName;
exports.KETCHER_MACROMOLECULES_ROOT_NODE_SELECTOR = Editor.KETCHER_MACROMOLECULES_ROOT_NODE_SELECTOR;
exports.MonomerLibraryConvertError = Editor.MonomerLibraryConvertError;
exports.MonomerLibraryUpdateError = Editor.MonomerLibraryUpdateError;
exports.NATURAL_AMINO_ACID_MODIFICATION_TYPE = Editor.NATURAL_AMINO_ACID_MODIFICATION_TYPE;
exports.provideEditorInstance = editorSingleton.provideEditorInstance;
exports.resetEditorInstance = editorSingleton.resetEditorInstance;
exports.setEditorInstance = editorSingleton.setEditorInstance;
exports.compareByTitleWithNaturalFirst = sort.compareByTitleWithNaturalFirst;
exports.compareStringsWithNaturalFirst = sort.compareStringsWithNaturalFirst;
exports.EditorHistory = EditorHistory.EditorHistory;
exports.FlexMode = FlexMode.FlexMode;
exports.SequenceMode = SequenceMode.SequenceMode;
exports.SnakeMode = SnakeMode.SnakeMode;
exports.DEFAULT_LAYOUT_MODE = index$5.DEFAULT_LAYOUT_MODE;
exports.HAS_CONTENT_LAYOUT_MODE = index$5.HAS_CONTENT_LAYOUT_MODE;
exports.isNodeRestrictedForHydrogenBondCreation = helpers$2.isNodeRestrictedForHydrogenBondCreation;
exports.isTwoStrandedNodeRestrictedForHydrogenBondCreation = helpers$2.isTwoStrandedNodeRestrictedForHydrogenBondCreation;
exports.editorEvents = editorEvents.editorEvents;
exports.hotkeysConfiguration = editorEvents.hotkeysConfiguration;
exports.renderersEvents = editorEvents.renderersEvents;
exports.resetEditorEvents = editorEvents.resetEditorEvents;
exports.provideEditorSettings = editorSettings.provideEditorSettings;
exports.isBaseTool = Tool.isBaseTool;
Object.defineProperty(exports, 'SCROLL_POSITION', {
	enumerable: true,
	get: function () { return Zoom.SCROLL_POSITION; }
});
exports.ZoomTool = Zoom.ZoomTool;
exports.SelectBase = SelectBase.SelectBase;
exports.SelectRectangle = SelectRectangle.SelectRectangle;
exports.SelectLasso = SelectLasso.SelectLasso;
exports.SelectFragment = SelectFragment.SelectFragment;
exports.buildRnaPresetConnections = rnaPresetConnections.buildRnaPresetConnections;
exports.getRnaPresetPhosphatePosition = rnaPresetConnections.getRnaPresetPhosphatePosition;
exports.toolsMap = index$6.toolsMap;
exports.MacromoleculesConverter = MacromoleculesConverter.MacromoleculesConverter;
Object.defineProperty(exports, 'MACROMOLECULES_BOND_TYPES', {
	enumerable: true,
	get: function () { return types$1.MACROMOLECULES_BOND_TYPES; }
});
Object.defineProperty(exports, 'ToolName', {
	enumerable: true,
	get: function () { return types$1.ToolName; }
});
exports.isMonomerItemPhosphate = monomerItem.isMonomerItemPhosphate;
exports.isMonomerItemSugar = monomerItem.isMonomerItemSugar;
//# sourceMappingURL=index.js.map
