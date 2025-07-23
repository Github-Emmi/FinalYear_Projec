from cloudinary_storage.storage import MediaCloudinaryStorage

class RawMediaCloudinaryStorage(MediaCloudinaryStorage):
    def __init__(self, *args, **kwargs):
        kwargs['resource_type'] = 'raw'  # Important for non-image files
        super().__init__(*args, **kwargs)
DEFAULT_FILE_STORAGE = 'schoolapp.storages.RawMediaCloudinaryStorage'   