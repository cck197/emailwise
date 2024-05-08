import db from "/app/db.server";

export async function getEmailGenerator(id, graphql) {
  const generator = await db.emailGenerator.findFirstOrThrow({ where: { id } });
  return supplementGenerator(generator, graphql);
}

export async function getSelectValues(tableName) {
  const table = db[tableName];
  const rows = await table.findMany({
    orderBy: { name: "asc" },
  });

  return rows.map((row) => ({
    value: row.id.toString(),
    label: row.name,
  }));
}

export async function getEmail(shop, emailGeneratorId) {
  let email;
  try {
    email = await db.email.findFirstOrThrow({
      where: {
        shop: shop,
        emailGeneratorId: emailGeneratorId,
      },
      orderBy: { createdAt: "desc" },
    });
  } catch (error) {
    email = null;
  }
  return email;
}

export async function getLLMProviders() {
  return getSelectValues("lLMProvider");
}

export async function getEmailProviders() {
  return getSelectValues("emailProvider");
}

export async function getEmailGenerators(shop, graphql) {
  const generators = await getEmailGeneratorsByShop(shop);

  return Promise.all(
    generators.map((generator) => supplementGenerator(generator, graphql)),
  );
}

export async function getEmailGeneratorsByShop(shop) {
  return await db.emailGenerator.findMany({
    where: {
      shop: shop,
    },
    orderBy: { id: "desc" },
    include: {
      emailProvider: {
        select: {
          name: true,
        },
      },
      llmProvider: {
        select: {
          name: true,
        },
      },
    },
  });
}

async function sendWebhook(payload) {
  const webhookUrl = process.env.WEBHOOK_URL;
  fetch(webhookUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then((response) => {
      console.log("Webhook sent successfully", response.ok);
    })
    .catch((error) => {
      console.error("Failed to send webhook", error);
    });
}

export async function generateEmail(id, generator, graphql) {
  const product = await supplementGenerator(generator, graphql);
  const payload = { id, data: { ...product, generator } };
  await sendWebhook(payload);
}

export async function upsertEmailGenerator(id, data, graphql) {
  const result =
    id === "new"
      ? await db.emailGenerator.create({ data })
      : await db.emailGenerator.update({
          where: { id: Number(id) },
          data,
        });
  await generateEmail(id, result, graphql);
  return result;
}

export async function getEmailGeneratorById(id) {
  return await db.emailGenerator.findFirstOrThrow({
    where: {
      id: id,
    },
    include: {
      emailProvider: {
        select: {
          name: true,
        },
      },
      llmProvider: {
        select: {
          name: true,
        },
      },
    },
  });
}

async function supplementGenerator(generator, graphql) {
  const response = await graphql(
    `
      query supplementGenerator($id: ID!) {
        product(id: $id) {
          title
          images(first: 1) {
            nodes {
              altText
              url
            }
          }
          description
        }
      }
    `,
    {
      variables: {
        id: generator.productId,
      },
    },
  );

  const {
    data: { product },
  } = await response.json();

  return {
    ...generator,
    productDeleted: !product?.title,
    productTitle: product?.title,
    productImage: product?.images?.nodes[0]?.url,
    productAlt: product?.images?.nodes[0]?.altText,
    productDescription: product?.description,
  };
}

export function validateEmailGenerator(data) {
  const errors = {};

  if (!data.name) {
    errors.name = "Name is required";
  }

  if (!data.productId) {
    errors.productId = "Product is required";
  }

  if (!data.emailProviderId) {
    errors.emailProviderId = "Email Provider is required";
  }

  if (!data.llmProviderId) {
    errors.llmProviderId = "AI Provider is required";
  }

  if (!data.emailPrivateKey) {
    errors.emailPrivateKey = "Private API key is required";
  }

  if (!data.llmPrivateKey) {
    errors.llmPrivateKey = "Private API key is required";
  }

  if (Object.keys(errors).length) {
    return errors;
  }
}
