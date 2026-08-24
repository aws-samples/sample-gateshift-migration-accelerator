import apiClient from './client';

export async function getPresignedUploadUrl(fileName: string): Promise<{
  uploadUrl: string;
  s3Key: string;
}> {
  const { data } = await apiClient.post('/uploads/presign', { fileName });
  return data;
}

export async function uploadToS3(uploadUrl: string, file: File): Promise<void> {
  await fetch(uploadUrl, {
    method: 'PUT',
    body: file,
    headers: { 'Content-Type': 'application/x-yaml' },
  });
}
