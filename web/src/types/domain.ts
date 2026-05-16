export type OrgType = "regulator" | "bank" | "mfs" | "nbfi";
export type Role = "superadmin" | "admin" | "manager" | "analyst" | "viewer";
export type Persona = "bfiu_analyst" | "bank_camlco" | "bfiu_director" | "bank_filer";
export type Severity = "critical" | "high" | "medium" | "low";
export type AlertStatus =
  | "open"
  | "reviewing"
  | "escalated"
  | "true_positive"
  | "false_positive";
export type CaseStatus =
  | "open"
  | "investigating"
  | "escalated"
  | "pending_action"
  | "closed_confirmed"
  | "closed_false_positive";
export type STRReportStatus =
  | "draft"
  | "submitted"
  | "under_review"
  | "flagged"
  | "confirmed"
  | "dismissed";

export interface Viewer {
  id: string;
  email: string;
  fullName: string;
  designation: string;
  role: Role;
  persona: Persona;
  orgId: string;
  orgName: string;
  orgType: OrgType;
}

export interface KpiStat {
  label: string;
  value: string;
  delta: string;
  detail: string;
}

export interface ThreatMapRow {
  channel: string;
  level: string;
  detail: string;
  signalCount: number;
  totalExposure: number;
}

export interface TrendPoint {
  month: string;
  alerts: number;
  strReports: number;
  cases: number;
  scans: number;
}

export interface AlertReason {
  rule: string;
  score: number;
  weight: number;
  explanation: string;
  evidence: Record<string, string | number | boolean>;
  recommendedAction?: string;
}

export interface NetworkNode {
  id: string;
  type: "account" | "phone" | "wallet" | "person" | "business" | "device";
  label: string;
  subtitle: string;
  riskScore: number;
  severity: Severity;
}

export interface NetworkEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  relation: string;
  amount?: number;
}

export interface NetworkGraph {
  focusEntityId: string;
  stats: {
    nodeCount: number;
    edgeCount: number;
    maxDepth: number;
    suspiciousPaths: number;
  };
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

export interface ActivityEvent {
  id: string;
  title: string;
  description: string;
  occurredAt: string;
  actor: string;
}

export interface ReportingHistoryItem {
  orgName: string;
  reportRef: string;
  reportedAt: string;
  channel: string;
  amount: number;
}

export interface EntitySummary {
  id: string;
  entityType: string;
  displayValue: string;
  displayName?: string;
  canonicalValue: string;
  riskScore: number;
  severity: Severity;
  confidence: number;
  status: string;
  reportCount: number;
  reportingOrgs: string[];
  totalExposure: number;
  firstSeen?: string;
  lastSeen?: string;
  tags: string[];
}

export interface EntityDossier extends EntitySummary {
  narrative: string;
  linkedCaseIds: string[];
  linkedAlertIds: string[];
  reportingHistory: ReportingHistoryItem[];
  connections: EntitySummary[];
  timeline: ActivityEvent[];
  graph: NetworkGraph;
}

export interface AlertSummary {
  id: string;
  title: string;
  description: string;
  alertType: string;
  riskScore: number;
  severity: Severity;
  status: AlertStatus;
  createdAt: string;
  orgName: string;
  entityId: string;
  reasons: AlertReason[];
  assignedTo?: string;
  caseId?: string;
}

export interface AlertDetail extends AlertSummary {
  graph: NetworkGraph;
  entity?: EntitySummary;
}

export interface AiExplanation {
  summary: string;
  whyItMatters: string;
  recommendedActions: string[];
}

export interface MatchSummary {
  id: string;
  entityId: string;
  matchKey: string;
  matchType: string;
  involvedOrgs: string[];
  involvedStrIds: string[];
  matchCount: number;
  totalExposure: number;
  riskScore: number;
  severity: Severity;
  status: string;
}

export type CrossBankPersonaView = "regulator" | "bank";

export interface CrossBankSummary {
  windowDays: number;
  entitiesFlaggedAcrossBanks: number;
  newThisWeek: number;
  highRiskCrossInstitution: number;
  totalExposure: number;
  crossBankAlertsCount: number;
  visibleMatchesCount: number;
  personaView: CrossBankPersonaView;
}

export interface CrossBankMatchView {
  id: string;
  entityId: string;
  matchKey: string;
  matchType: string;
  involvedOrgs: string[];
  bankCount: number;
  matchCount: number;
  totalExposure: number;
  riskScore: number;
  severity: Severity;
  status: string;
  firstSeen: string | null;
}

export interface CrossBankSeverityBreakdown {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface CrossBankHeatmapBucket {
  label: string;
  matchCount: number;
  severityBreakdown: CrossBankSeverityBreakdown;
}

export interface CrossBankHeatmap {
  windowDays: number;
  buckets: CrossBankHeatmapBucket[];
  personaView: CrossBankPersonaView;
}

export interface CrossBankEntityRow {
  entityId: string;
  display: string;
  entityType: string;
  riskScore: number;
  severity: Severity;
  bankCount: number;
  involvedOrgs: string[];
  totalExposure: number;
}

// Trade transaction types — migration 027 + Phase B. Keep in sync with the
// engine TradeSide / PaymentMode / TradeStatus literals.
export type TradeSide = "import" | "export" | "royalty";

export type PaymentMode =
  | "lc_sight"
  | "lc_usance"
  | "lc_btb"
  | "lc_transferable"
  | "lc_standby"
  | "lc_red_clause"
  | "open_account"
  | "cash_in_advance"
  | "documentary_collection_da"
  | "documentary_collection_dp"
  | "royalty_fee"
  | "other";

export type TradeStatus =
  | "open"
  | "in_progress"
  | "settled"
  | "overdue"
  | "cancelled"
  | "flagged";

export interface TradeTransactionSummary {
  id: string;
  orgId: string;
  tradeRef: string;
  tradeSide: TradeSide;
  paymentMode: PaymentMode;
  subjectName: string;
  subjectAccount: string;
  counterpartyName: string;
  counterpartyCountry: string;
  hsCode?: string | null;
  invoiceValue: number;
  declaredValue?: number | null;
  settlementAmount?: number | null;
  currency: string;
  status: TradeStatus;
  shipmentDate?: string | null;
  settlementDate?: string | null;
  lcReference?: string | null;
  blNumber?: string | null;
  createdAt: string;
}

export interface TradeTransactionDetail extends TradeTransactionSummary {
  lcIssuingBank?: string | null;
  lcAdvisingBank?: string | null;
  lcConfirmingBank?: string | null;
  lcIssueDate?: string | null;
  lcExpiryDate?: string | null;
  lcafReference?: string | null;
  ircOrErc?: string | null;
  subjectBank?: string | null;
  subjectCountry: string;
  counterpartyBank?: string | null;
  counterpartyAccount?: string | null;
  notifyParty?: string | null;
  consignee?: string | null;
  goodsDescription?: string | null;
  quantity?: number | null;
  unit?: string | null;
  unitPrice?: number | null;
  marketReferenceValue?: number | null;
  bdtEquivalent?: number | null;
  vessel?: string | null;
  containerNumbers: string[];
  portOfLoading?: string | null;
  portOfDischarge?: string | null;
  transshipmentPorts: string[];
  beNumber?: string | null;
  beDate?: string | null;
  insuranceValue?: number | null;
  discrepancies: string[];
  linkedStrId?: string | null;
  linkedCaseId?: string | null;
  metadata: Record<string, unknown>;
  updatedAt: string;
}

export interface TypologySummary {
  id: string;
  title: string;
  category: string;
  channels: string[];
  indicators: string[];
  narrative: string;
  // Migration 026 — BD-specific TBML avenues carry these BFIU-aligned fields.
  predicateOffences?: PredicateOffence[];
  mlpaSection?: MlpaSection | null;
  bfiuAvenueRef?: string | null;
}

export interface DetectionRunSummary {
  id: string;
  fileName: string;
  status: "pending" | "processing" | "completed" | "failed";
  alertsGenerated: number;
  accountsScanned: number;
  txCount: number;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
}

export interface FlaggedAccount {
  entityId: string;
  accountNumber: string;
  accountName: string;
  score: number;
  severity: Severity;
  summary: string;
  matchedBanks: number;
  totalExposure: number;
  tags: string[];
  linkedAlertId?: string;
  linkedCaseId?: string;
}

export interface DetectionRunDetail extends DetectionRunSummary {
  runType: string;
  summary: string;
  flaggedAccounts: FlaggedAccount[];
  error?: string;
}

export type CaseVariant =
  | "standard"
  | "proposal"
  | "rfi"
  | "operation"
  | "project"
  | "escalated"
  | "complaint"
  | "adverse_media";

export type ProposalDecision = "approved" | "rejected" | "pending";

export interface CaseSummary {
  id: string;
  caseRef: string;
  title: string;
  summary: string;
  severity: Severity;
  status: CaseStatus;
  totalExposure: number;
  assignedTo?: string;
  linkedEntityIds: string[];
  linkedAlertIds: string[];
  variant: CaseVariant;
  parentCaseId?: string | null;
  proposalDecision?: ProposalDecision | null;
  requestedBy?: string | null;
  requestedFrom?: string | null;
  predicateOffences: PredicateOffence[];
}

export interface CaseNote {
  actorUserId: string;
  actorRole: string;
  note: string;
  occurredAt: string;
}

export interface CaseWorkspace extends CaseSummary {
  timeline: ActivityEvent[];
  evidenceEntities: EntitySummary[];
  notes: CaseNote[];
  graph?: NetworkGraph;
  proposalDecidedBy?: string | null;
  proposalDecidedAt?: string | null;
}

export interface ComplianceScore {
  orgName: string;
  submissionTimeliness: number;
  alertConversion: number;
  peerCoverage: number;
  score: number;
}

export interface ApiKeySummary {
  id: string;
  name: string;
  lastUsedAt: string;
  scope: string[];
}

export interface AdminSummary {
  orgName: string;
  orgType: OrgType;
  plan: string;
  teamMembers: number;
  activeRules: number;
  totalRules: number;
  apiIntegrations: number;
  crossBankHits: number;
  detectionRuns: number;
  syntheticBackfillAvailable: boolean;
}

export interface AdminSettings {
  orgName: string;
  orgType: OrgType;
  plan: string;
  bankCode?: string;
  authConfigured: boolean;
  storageConfigured: boolean;
  demoModeEnabled: boolean;
  goamlSyncEnabled: boolean;
  goamlBaseUrlConfigured: boolean;
  environment: string;
  appVersion: string;
  uploadsBucket: string;
  exportsBucket: string;
  syntheticBackfillAvailable: boolean;
}

export interface AdminTeamMember {
  id: string;
  fullName: string;
  designation?: string;
  role: Role;
  persona: Persona;
}

export interface AdminRuleSummary {
  code: string;
  name: string;
  description: string;
  category: string;
  source: string;
  isActive: boolean;
  isSystem: boolean;
  weight: number;
  version: number;
  threshold?: number;
}

export interface AdminIntegration {
  id: string;
  name: string;
  status: string;
  detail: string;
  scope: string[];
  lastUsedAt?: string;
}

export interface SyntheticBackfillPlan {
  datasetRoot: string;
  statements: number;
  entities: number;
  matches: number;
  transactions: number;
  connections: number;
}

export interface SyntheticBackfillResult {
  datasetRoot: string;
  organizations: number;
  entities: number;
  connections: number;
  matches: number;
  transactions: number;
  strReports: number;
  alerts: number;
  cases: number;
  reportingOrgs: Record<string, number>;
}

export interface DeploymentCheck {
  name: string;
  status: string;
  required: boolean;
  detail: string;
  metadata: Record<string, unknown>;
}

export interface DeploymentReadiness {
  status: "ready" | "not_ready";
  version: string;
  environment: string;
  checks: DeploymentCheck[];
}

export interface STRLifecycleEvent {
  action: string;
  actorUserId: string;
  actorRole: string;
  actorOrgType: string;
  fromStatus?: string | null;
  toStatus?: string | null;
  note?: string | null;
  occurredAt: string;
}

export interface STREnrichment {
  draftNarrative: string;
  missingFields: string[];
  categorySuggestion: string;
  severitySuggestion: string;
  triggerFacts: string[];
  extractedEntities: {
    entityType: string;
    value: string;
    confidence: number;
  }[];
  generatedAt: string;
}

export interface STRReviewState {
  assignedTo?: string | null;
  notes: {
    actorUserId: string;
    actorRole: string;
    note: string;
    occurredAt: string;
  }[];
  statusHistory: STRLifecycleEvent[];
}

export type ReportType =
  | "str"
  | "sar"
  | "ctr"
  | "tbml"
  | "complaint"
  | "ier"
  | "internal"
  | "adverse_media_str"
  | "adverse_media_sar"
  | "escalated"
  | "additional_info";

export type IERDirection = "inbound" | "outbound";

export interface STRReportSummary {
  id: string;
  orgId: string;
  orgName: string;
  reportRef: string;
  reportType: ReportType;
  status: STRReportStatus;
  subjectName?: string | null;
  subjectAccount?: string | null;
  subjectBank?: string | null;
  totalAmount: number;
  currency: string;
  transactionCount: number;
  primaryChannel?: string | null;
  category: string;
  autoRiskScore?: number | null;
  crossBankHit: boolean;
  reportedAt?: string | null;
  createdAt: string;
  updatedAt?: string | null;
  supplementsReportId?: string | null;
  ierDirection?: IERDirection | null;
  ierCounterpartyFiu?: string | null;
  mediaSource?: string | null;
  predicateOffences: PredicateOffence[];
}

export interface STRReportDetail extends STRReportSummary {
  subjectPhone?: string | null;
  subjectWallet?: string | null;
  subjectNid?: string | null;
  channels: string[];
  dateRangeStart?: string | null;
  dateRangeEnd?: string | null;
  narrative?: string | null;
  matchedEntityIds: string[];
  submittedBy?: string | null;
  reviewedBy?: string | null;
  metadata: Record<string, unknown>;
  enrichment?: STREnrichment | null;
  review: STRReviewState;
  mediaUrl?: string | null;
  mediaPublishedAt?: string | null;
  ierCounterpartyCountry?: string | null;
  ierEgmontRef?: string | null;
  ierRequestNarrative?: string | null;
  ierResponseNarrative?: string | null;
  ierDeadline?: string | null;
  tbmlInvoiceValue?: number | null;
  tbmlDeclaredValue?: number | null;
  tbmlLcReference?: string | null;
  tbmlHsCode?: string | null;
  tbmlCommodity?: string | null;
  tbmlCounterpartyCountry?: string | null;
}

export type RecipientType =
  | "law_enforcement"
  | "regulator"
  | "foreign_fiu"
  | "prosecutor"
  | "other";

// Named Bangladesh recipient authority under MLPA 2012 §23 + §24 + BFIU
// Circular 22. Keep in sync with the migration 024 CHECK constraint and the
// engine-side RecipientAuthority Literal.
export type RecipientAuthority =
  | "bangladesh_police_cid"
  | "anti_corruption_commission"
  | "national_board_of_revenue"
  | "dept_narcotics_control"
  | "bangladesh_securities_exchange_commission"
  | "insurance_dev_regulatory_authority"
  | "microcredit_regulatory_authority"
  | "dgfi"
  | "nsi"
  | "court_or_investigating_officer"
  | "foreign_fiu_egmont"
  | "bb_internal_dept"
  | "peer_reporting_org_circular_22";

// MLPA 2012 §2(cc) predicate offence codes. Each STR / Case / Dissemination
// can cite multiple. Keep in sync with the engine PredicateOffence Literal and
// the CHECK constraint in migration 025.
export type PredicateOffence =
  | "corruption_and_bribery"
  | "counterfeiting_currency"
  | "counterfeiting_deeds_and_documents"
  | "extortion"
  | "fraud"
  | "forgery"
  | "illegal_trade_firearms"
  | "illegal_trade_narcotics"
  | "illegal_trade_stolen_goods"
  | "kidnapping_restraint_hostage"
  | "murder_grievous_injury"
  | "trafficking_women_children"
  | "black_marketing"
  | "smuggling_currency"
  | "theft_robbery_dacoity_piracy_hijacking"
  | "human_trafficking"
  | "dowry"
  | "smuggling_customs_excise"
  | "tax_related_offences"
  | "infringement_intellectual_property"
  | "terrorism_or_terrorist_financing"
  | "adulteration_title_infringement"
  | "environmental_offences"
  | "sexual_exploitation"
  | "insider_trading_market_manipulation"
  | "organized_crime"
  | "racketeering"
  | "other_bb_gazetted";

// Display labels for the 28 predicate-offence codes — surfaced by UI
// dropdowns and detail panels. Comments cite MLPA 2012 §2(cc) clause number.
export const PREDICATE_OFFENCE_LABELS: Record<PredicateOffence, string> = {
  corruption_and_bribery: "(1) Corruption and bribery",
  counterfeiting_currency: "(2) Counterfeiting currency",
  counterfeiting_deeds_and_documents: "(3) Counterfeiting deeds + documents",
  extortion: "(4) Extortion",
  fraud: "(5) Fraud",
  forgery: "(6) Forgery",
  illegal_trade_firearms: "(7) Illegal trade in firearms",
  illegal_trade_narcotics: "(8) Illegal trade in narcotic drugs / psychotropics",
  illegal_trade_stolen_goods: "(9) Illegal trade in stolen and other goods",
  kidnapping_restraint_hostage: "(10) Kidnapping / illegal restraint / hostage-taking",
  murder_grievous_injury: "(11) Murder / grievous physical injury",
  trafficking_women_children: "(12) Trafficking of women and children",
  black_marketing: "(13) Black marketing",
  smuggling_currency: "(14) Smuggling of domestic and foreign currency",
  theft_robbery_dacoity_piracy_hijacking: "(15) Theft / robbery / dacoity / piracy / hijacking",
  human_trafficking: "(16) Human trafficking",
  dowry: "(17) Dowry",
  smuggling_customs_excise: "(18) Smuggling / customs + excise offences (TBML)",
  tax_related_offences: "(19) Tax-related offences",
  infringement_intellectual_property: "(20) Infringement of intellectual property rights",
  terrorism_or_terrorist_financing: "(21) Terrorism / terrorist financing",
  adulteration_title_infringement: "(22) Adulteration / title infringement in manufacture",
  environmental_offences: "(23) Environmental offences",
  sexual_exploitation: "(24) Sexual exploitation",
  insider_trading_market_manipulation: "(25) Insider trading / market manipulation",
  organized_crime: "(26) Organized crime",
  racketeering: "(27) Racketeering",
  other_bb_gazetted: "(28) Other — declared predicate by BB gazette",
};

// MLPA / ATA enabling clause cited on each dissemination.
export type MlpaSection =
  | "mlpa_23_1_a"
  | "mlpa_23_1_b"
  | "mlpa_23_1_c"
  | "mlpa_23_1_d"
  | "mlpa_23_1_e"
  | "mlpa_23_1_f"
  | "mlpa_23_1_g"
  | "mlpa_24_3"
  | "mlpa_24_4"
  | "ata_15_1_a"
  | "ata_15_1_b"
  | "ata_15_1_c"
  | "ata_15_1_d"
  | "ata_15_1_e"
  | "ata_15_1_f"
  | "ata_15_1_g";

export type Classification =
  | "public"
  | "internal"
  | "confidential"
  | "restricted"
  | "secret";

export interface DisseminationSummary {
  id: string;
  orgId: string;
  orgName: string;
  disseminationRef: string;
  recipientAgency: string;
  recipientType: RecipientType;
  recipientAuthority?: RecipientAuthority | null;
  mlpaSection?: MlpaSection | null;
  circular22Exchange: boolean;
  predicateOffences: PredicateOffence[];
  subjectSummary: string;
  classification: Classification;
  disseminatedBy?: string | null;
  disseminatedAt: string;
  linkedReportCount: number;
  linkedEntityCount: number;
  linkedCaseCount: number;
  createdAt: string;
}

export interface DisseminationDetail extends DisseminationSummary {
  linkedReportIds: string[];
  linkedEntityIds: string[];
  linkedCaseIds: string[];
  metadata: Record<string, unknown>;
}

export type SavedQueryType =
  | "entity_search"
  | "transaction_search"
  | "str_filter"
  | "alert_filter"
  | "case_filter"
  | "custom";

export interface SavedQuerySummary {
  id: string;
  orgId: string;
  userId: string;
  name: string;
  description?: string | null;
  queryType: SavedQueryType;
  isShared: boolean;
  lastRunAt?: string | null;
  runCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface SavedQueryDetail extends SavedQuerySummary {
  queryDefinition: Record<string, unknown>;
}

export interface DiagramSummary {
  id: string;
  orgId: string;
  createdBy?: string | null;
  title: string;
  description?: string | null;
  linkedCaseId?: string | null;
  linkedStrId?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface DiagramDetail extends DiagramSummary {
  graphDefinition: Record<string, unknown>;
}

export type MatchExecutionStatus = "pending" | "running" | "completed" | "failed";

export interface MatchExecutionSummary {
  id: string;
  definitionId: string;
  executedAt: string;
  executedBy?: string | null;
  hitCount: number;
  executionStatus: MatchExecutionStatus;
  resultsSummary: Record<string, unknown>;
}

export interface MatchDefinitionSummary {
  id: string;
  orgId: string;
  name: string;
  description?: string | null;
  isActive: boolean;
  createdBy?: string | null;
  createdAt: string;
  updatedAt: string;
  lastExecutionAt?: string | null;
  totalHits: number;
}

export interface MatchDefinitionDetail extends MatchDefinitionSummary {
  definition: Record<string, unknown>;
  recentExecutions: MatchExecutionSummary[];
}

export type ReferenceTableName =
  | "banks"
  | "branches"
  | "countries"
  | "channels"
  | "categories"
  | "currencies"
  | "agencies";

export interface ReferenceEntry {
  id: string;
  tableName: ReferenceTableName;
  code: string;
  value: string;
  description?: string | null;
  parentCode?: string | null;
  metadata: Record<string, unknown>;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ReferenceTableMeta {
  tableName: ReferenceTableName;
  activeCount: number;
  totalCount: number;
}

export interface ReportsByTypeByMonth {
  month: string;
  reportType: string;
  count: number;
}

export interface ReportsByOrg {
  orgName: string;
  count: number;
}

export interface CtrVolumeByMonth {
  month: string;
  count: number;
  totalAmount: number;
}

export interface DisseminationsByAgency {
  recipientAgency: string;
  recipientType: string;
  count: number;
}

export interface CaseOutcomeBreakdown {
  status: string;
  count: number;
}

export interface TimeToReviewAverage {
  reportType: string;
  averageHours: number;
  sampleSize: number;
}

export interface OperationalStatistics {
  reportsByTypeByMonth: ReportsByTypeByMonth[];
  reportsByOrg: ReportsByOrg[];
  ctrVolumeByMonth: CtrVolumeByMonth[];
  disseminationsByAgency: DisseminationsByAgency[];
  caseOutcomes: CaseOutcomeBreakdown[];
  timeToReview: TimeToReviewAverage[];
  generatedAt: string;
}

export interface ScheduleEntry {
  name: string;
  description: string;
  cron: string;
  task: string;
  status: string;
  lastRunAt?: string | null;
  nextRunAt?: string | null;
}

export interface ScheduleWorker {
  hostname: string;
  alive: boolean;
}

export interface ScheduleList {
  schedules: ScheduleEntry[];
  workers: ScheduleWorker[];
  generatedAt: string;
}

export interface IERSummary {
  id: string;
  reportRef: string;
  status: string;
  direction: IERDirection;
  counterpartyFiu: string;
  counterpartyCountry?: string | null;
  egmontRef?: string | null;
  deadline?: string | null;
  hasResponse: boolean;
  orgName: string;
  createdAt: string;
  updatedAt?: string | null;
}

export interface IERDetail extends IERSummary {
  requestNarrative?: string | null;
  responseNarrative?: string | null;
  narrative?: string | null;
  linkedEntityIds: string[];
  reportedAt?: string | null;
}
