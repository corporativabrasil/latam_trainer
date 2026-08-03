export type Project={id:number;title:string;client_company:string;country:string;audience:string;objective:string;spanish_variant:string;formality:string;modality:string;created_at:string};
export type Material={id:number;project_id:number;filename:string;content_type:string;status:string;extracted_text:string;created_at:string};
export type Translation={id:number;material_id:number;mode:string;source_text:string;translated_text:string;approved:boolean;created_at:string};
export type Glossary={id:number;project_id:number;source_term:string;target_term:string;notes:string};
